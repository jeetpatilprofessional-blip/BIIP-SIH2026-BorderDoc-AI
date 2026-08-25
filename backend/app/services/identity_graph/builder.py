# BIIP-SIH2026 Identity Graph Builder
import uuid
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from sqlmodel import Session, select
import numpy as np

from app.services.identity_graph.models import (
    GraphNode,
    GraphEdge,
    GraphSummary,
    Conflict,
    NodeType,
    EdgeType,
    ConflictSeverity,
)
from app.models.case import Case
from app.models.person import Person
from app.models.document import Document, DocumentType
from app.models.document_field import DocumentField
from app.models.face_result import FaceResult, FaceMatchResult
from app.models.identity_graph import IdentityNode, IdentityEdge
from app.models.evidence import EvidenceAtom, EvidenceSource, EvidenceSeverity
from app.core.database import get_session


class IdentityGraphBuilder:
    """Build and analyze cross-document identity graph"""

    def __init__(self, session: Session):
        self.session = session
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.conflicts: List[Conflict] = []
        self.face_embeddings: Dict[str, np.ndarray] = {}  # node_id -> embedding

    def build(self, case_id: str) -> GraphSummary:
        """Build complete identity graph for a case"""
        # Clear state
        self.nodes = {}
        self.edges = []
        self.conflicts = []
        self.face_embeddings = {}

        # 1. Create person node
        person = self.session.exec(
            select(Person).where(Person.case_id == case_id)
        ).first()

        if person:
            person_node = self._create_person_node(person)
            self.nodes[person_node.id] = person_node

        # 2. Create document nodes and link to person
        documents = self.session.exec(
            select(Document).where(Document.case_id == case_id)
        ).all()

        doc_nodes = {}
        for doc in documents:
            doc_node = self._create_document_node(doc)
            self.nodes[doc_node.id] = doc_node
            doc_nodes[doc.id] = doc_node

            # Link to person
            if person:
                self._add_edge(
                    source=person_node.id,
                    target=doc_node.id,
                    edge_type=EdgeType.BELONGS_TO,
                    weight=1.0,
                )

        # 3. Create face nodes and link to documents
        face_results = self.session.exec(
            select(FaceResult).where(FaceResult.case_id == case_id)
        ).all()

        face_nodes = {}
        for fr in face_results:
            face_node = self._create_face_node(fr)
            self.nodes[face_node.id] = face_node
            face_nodes[fr.id] = face_node

            # Store embedding for clustering
            if fr.embedding:
                import pickle
                self.face_embeddings[face_node.id] = pickle.loads(fr.embedding)

            # Link to document - use compared_to_document_id for match results
            doc_id = fr.compared_to_document_id or fr.document_id
            if doc_id and doc_id in doc_nodes:
                edge_type = EdgeType.MATCHES if fr.match_result == FaceMatchResult.MATCH else EdgeType.ASSOCIATED_WITH
                weight = fr.match_score if fr.match_result == FaceMatchResult.MATCH else 0.9
                self._add_edge(
                    source=doc_nodes[doc_id].id,
                    target=face_node.id,
                    edge_type=edge_type,
                    weight=weight,
                )

        # 4. Cross-document field consistency edges
        self._add_cross_document_edges(documents)

        # 5. Face clustering for identity fragmentation detection
        self._cluster_faces(face_nodes)

        # 6. Detect conflicts
        self._detect_conflicts(documents, face_results)

        # 7. Persist to database
        self._persist_graph(case_id)

        # Build summary
        return GraphSummary(
            case_id=case_id,
            nodes=list(self.nodes.values()),
            edges=self.edges,
            conflicts=self.conflicts,
            face_clusters=self._get_face_clusters(),
            identity_fragmentation_detected=self._check_identity_fragmentation(),
            multiple_identities_detected=self._check_multiple_identities(),
            statistics={
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "total_conflicts": len(self.conflicts),
                "person_nodes": sum(1 for n in self.nodes.values() if n.node_type == NodeType.PERSON),
                "document_nodes": sum(1 for n in self.nodes.values() if n.node_type != NodeType.PERSON and n.node_type != NodeType.FACE),
                "face_nodes": sum(1 for n in self.nodes.values() if n.node_type == NodeType.FACE),
            },
        )

    def _create_person_node(self, person: Person) -> GraphNode:
        return GraphNode(
            id=f"person_{person.id}",
            node_type=NodeType.PERSON,
            entity_id=person.id,
            label=f"Person: {person.primary_name or 'Unknown'}",
            properties={
                "primary_name": person.primary_name,
                "primary_dob": person.primary_dob,
                "primary_nationality": person.primary_nationality,
                "primary_gender": person.primary_gender,
                "identity_confidence": person.identity_confidence,
            },
            confidence=person.identity_confidence or 0.5,
        )

    def _create_document_node(self, document: Document) -> GraphNode:
        node_type_map = {
            DocumentType.PASSPORT: NodeType.PASSPORT,
            DocumentType.VISA: NodeType.VISA,
            DocumentType.NATIONAL_ID: NodeType.NATIONAL_ID,
            DocumentType.DRIVING_LICENCE: NodeType.DRIVING_LICENCE,
            DocumentType.PERMIT: NodeType.PERMIT,
            DocumentType.TRAVEL_AUTHORIZATION: NodeType.TRAVEL_AUTHORIZATION,
        }

        # Get key fields for label
        fields = self.session.exec(
            select(DocumentField).where(DocumentField.document_id == document.id)
        ).all()
        field_map = {f.field_name: f.value for f in fields}

        if document.document_type == DocumentType.PASSPORT:
            label = f"Passport: {field_map.get('passport_number', 'N/A')}"
        elif document.document_type == DocumentType.VISA:
            label = f"Visa: {field_map.get('visa_number', 'N/A')}"
        else:
            label = f"{document.document_type.value}: {field_map.get('id_number', 'N/A')}"

        return GraphNode(
            id=f"doc_{document.id}",
            node_type=node_type_map.get(document.document_type, NodeType.PASSPORT),
            entity_id=document.id,
            label=label,
            properties={
                "document_type": document.document_type.value,
                "document_subtype": document.document_subtype,
                "status": document.status.value,
                "mrz_valid": document.mrz_valid,
                "quality_score": document.quality_score,
                "fields": field_map,
            },
            confidence=document.quality_score or 0.5,
        )

    def _create_face_node(self, face_result: FaceResult) -> GraphNode:
        source_label = "Live Face" if face_result.source_type == "LIVE_CAPTURE" else "Document Photo"

        return GraphNode(
            id=f"face_{face_result.id}",
            node_type=NodeType.FACE,
            entity_id=face_result.id,
            label=f"{source_label} (Quality: {face_result.quality_score:.2f})",
            properties={
                "source_type": face_result.source_type,
                "quality_score": face_result.quality_score,
                "liveness_result": face_result.liveness_result.value if face_result.liveness_result else "NOT_CHECKED",
                "match_result": face_result.match_result.value if face_result.match_result else None,
                "match_score": face_result.match_score,
                "compared_to_document_id": face_result.compared_to_document_id,
            },
            confidence=face_result.quality_score,
        )

    def _add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType,
        weight: float,
        properties: Dict[str, Any] = None,
        evidence_ids: List[str] = None,
    ):
        edge = GraphEdge(
            id=f"edge_{uuid.uuid4().hex[:8]}",
            source=source,
            target=target,
            edge_type=edge_type,
            weight=weight,
            properties=properties or {},
            evidence_ids=evidence_ids or [],
        )
        self.edges.append(edge)

    def _add_cross_document_edges(self, documents: List[Document]):
        """Add edges between documents based on field references"""
        # Passport -> Visa (visa references passport)
        passports = [d for d in documents if d.document_type == DocumentType.PASSPORT]
        visas = [d for d in documents if d.document_type == DocumentType.VISA]

        for passport in passports:
            p_fields = self.session.exec(
                select(DocumentField).where(DocumentField.document_id == passport.id)
            ).all()
            p_field_map = {f.field_name: f.value for f in p_fields}
            passport_num = p_field_map.get("passport_number") or p_field_map.get("mrz_passport_number")

            for visa in visas:
                v_fields = self.session.exec(
                    select(DocumentField).where(DocumentField.document_id == visa.id)
                ).all()
                v_field_map = {f.field_name: f.value for f in v_fields}
                visa_passport_ref = v_field_map.get("passport_number")

                if passport_num and visa_passport_ref:
                    matches = self._normalize(passport_num) == self._normalize(visa_passport_ref)
                    self._add_edge(
                        source=f"doc_{visa.id}",
                        target=f"doc_{passport.id}",
                        edge_type=EdgeType.REFERENCES if matches else EdgeType.CONFLICTS_WITH,
                        weight=0.9 if matches else 0.8,
                        properties={
                            "field": "passport_number",
                            "passport_value": passport_num,
                            "visa_value": visa_passport_ref,
                            "matches": matches,
                        },
                    )

    def _cluster_faces(self, face_nodes: Dict[str, GraphNode]):
        """Cluster faces by embedding similarity to detect identity fragmentation"""
        if len(self.face_embeddings) < 2:
            return

        node_ids = list(self.face_embeddings.keys())
        embeddings = [self.face_embeddings[nid] for nid in node_ids]

        # Compute pairwise similarities
        clusters = []
        assigned = set()

        for i, nid_i in enumerate(node_ids):
            if nid_i in assigned:
                continue

            cluster = [nid_i]
            assigned.add(nid_i)

            for j, nid_j in enumerate(node_ids):
                if i == j or nid_j in assigned:
                    continue

                sim = float(np.dot(embeddings[i], embeddings[j]))
                if sim >= 0.5:  # Threshold for same person
                    cluster.append(nid_j)
                    assigned.add(nid_j)

            if len(cluster) > 0:
                clusters.append({
                    "cluster_id": f"face_cluster_{len(clusters)}",
                    "nodes": cluster,
                    "size": len(cluster),
                    "avg_similarity": self._compute_cluster_similarity(cluster, embeddings, node_ids),
                })

                # Add MATCHES edges within cluster
                for idx_a, nid_a in enumerate(cluster):
                    for nid_b in cluster[idx_a + 1:]:
                        sim = float(np.dot(
                            self.face_embeddings[nid_a],
                            self.face_embeddings[nid_b]
                        ))
                        self._add_edge(
                            source=nid_a,
                            target=nid_b,
                            edge_type=EdgeType.MATCHES,
                            weight=sim,
                            properties={"similarity": sim},
                        )

    def _compute_cluster_similarity(self, cluster: List[str], embeddings: List[np.ndarray], node_ids: List[str]) -> float:
        """Compute average pairwise similarity in cluster"""
        if len(cluster) < 2:
            return 1.0

        idx_map = {nid: i for i, nid in enumerate(node_ids)}
        similarities = []

        for i, nid_a in enumerate(cluster):
            for nid_b in cluster[i + 1:]:
                sim = float(np.dot(embeddings[idx_map[nid_a]], embeddings[idx_map[nid_b]]))
                similarities.append(sim)

        return float(np.mean(similarities)) if similarities else 1.0

    def _get_face_clusters(self) -> List[Dict[str, Any]]:
        """Get face clusters for summary"""
        # Re-extract from edges
        clusters = []
        visited = set()

        for edge in self.edges:
            if edge.edge_type == EdgeType.MATCHES:
                if edge.source not in visited and edge.target not in visited:
                    # Find all connected nodes
                    cluster_nodes = set([edge.source, edge.target])
                    # Expand cluster (simplified)
                    for e in self.edges:
                        if e.edge_type == EdgeType.MATCHES:
                            if e.source in cluster_nodes or e.target in cluster_nodes:
                                cluster_nodes.add(e.source)
                                cluster_nodes.add(e.target)

                    if cluster_nodes:
                        clusters.append({
                            "nodes": list(cluster_nodes),
                            "size": len(cluster_nodes),
                        })
                        visited.update(cluster_nodes)

        return clusters

    def _detect_conflicts(self, documents: List[Document], face_results: List[FaceResult]):
        """Detect conflicts in the identity graph"""
        # Field conflicts across documents
        field_groupings = [
            ("birth_date", ["birth_date", "date_of_birth", "dob"]),
            ("passport_number", ["passport_number", "doc_number", "document_number"]),
            ("nationality", ["nationality"]),
            ("surname", ["surname"]),
            ("given_names", ["given_names"]),
        ]

        for canonical_name, aliases in field_groupings:
            values = {}
            for doc in documents:
                fields = self.session.exec(
                    select(DocumentField).where(
                        DocumentField.document_id == doc.id,
                        DocumentField.field_name.in_(aliases)
                    )
                ).all()

                for f in fields:
                    if f.value:
                        norm_val = self._normalize(f.value)
                        if norm_val not in values:
                            values[norm_val] = []
                        values[norm_val].append((f"doc_{doc.id}", f.value, f.source))

            # If multiple different values for same field
            if len(values) > 1:
                # Determine severity
                if canonical_name in ["passport_number", "birth_date"]:
                    severity = ConflictSeverity.CRITICAL
                elif canonical_name == "nationality":
                    severity = ConflictSeverity.HIGH
                else:
                    severity = ConflictSeverity.MEDIUM

                # Create conflict
                all_nodes = []
                for val, occurrences in values.items():
                    for node_id, orig_val, source in occurrences:
                        all_nodes.append(node_id)

                conflict_type = "CROSS_FIELD_CONFLICT_DOB" if canonical_name == "birth_date" else f"{canonical_name.upper()}_MISMATCH"
                conflict = Conflict(
                    conflict_id=f"conflict_{uuid.uuid4().hex[:8]}",
                    conflict_type=conflict_type,
                    severity=severity,
                    description=f"{canonical_name} has {len(values)} different values across documents",
                    nodes_involved=all_nodes,
                    edges_involved=[],
                    evidence_ids=[],
                    suggested_action="Manual verification required",
                )
                self.conflicts.append(conflict)

        # Face mismatch conflicts
        for fr in face_results:
            if fr.match_result == FaceMatchResult.MISMATCH and fr.compared_to_document_id:
                conflict = Conflict(
                    conflict_id=f"conflict_{uuid.uuid4().hex[:8]}",
                    conflict_type="FACE_MISMATCH",
                    severity=ConflictSeverity.CRITICAL,
                    description=f"Live face does not match document photo (score: {fr.match_score:.2f})",
                    nodes_involved=[f"face_{fr.id}", f"doc_{fr.compared_to_document_id}"],
                    edges_involved=[],
                    evidence_ids=[],
                    suggested_action="Escalate for manual inspection",
                )
                self.conflicts.append(conflict)
                # Add CONFLICTS_WITH edge for the face mismatch
                if f"face_{fr.id}" in self.nodes and f"doc_{fr.compared_to_document_id}" in self.nodes:
                    self._add_edge(
                        source=f"face_{fr.id}",
                        target=f"doc_{fr.compared_to_document_id}",
                        edge_type=EdgeType.CONFLICTS_WITH,
                        weight=1.0 - fr.match_score,
                        properties={
                            "conflict_type": "FACE_MISMATCH",
                            "match_score": fr.match_score,
                            "description": conflict.description,
                        },
                    )

        # Add CONFLICTS_WITH edges for field conflicts
        for conflict in self.conflicts:
            if len(conflict.nodes_involved) >= 2:
                for i, node_a in enumerate(conflict.nodes_involved):
                    for node_b in conflict.nodes_involved[i+1:]:
                        if node_a in self.nodes and node_b in self.nodes:
                            self._add_edge(
                                source=node_a,
                                target=node_b,
                                edge_type=EdgeType.CONFLICTS_WITH,
                                weight=1.0 if conflict.severity == ConflictSeverity.CRITICAL else 0.7,
                                properties={
                                    "conflict_type": conflict.conflict_type,
                                    "field": conflict.conflict_type.replace("_MISMATCH", "").lower(),
                                    "description": conflict.description,
                                    "conflict_id": conflict.conflict_id,
                                },
                            )

    def _check_identity_fragmentation(self) -> bool:
        """Check if same person appears with different identities"""
        # If we have multiple face clusters for documents belonging to same person
        face_clusters = self._get_face_clusters()
        if len(face_clusters) > 1:
            return True
        # Or if we have conflicts in cross-field identity data
        return len(self.conflicts) > 0

    def _check_multiple_identities(self) -> bool:
        """Check if multiple persons share same identity documents"""
        # This would require checking across cases - simplified for prototype
        return False

    def _normalize(self, value: str) -> str:
        """Normalize for comparison"""
        import re
        normalized = re.sub(r"\s+", " ", value.strip().upper())
        normalized = normalized.replace("Ø", "O").replace("Å", "A").replace("Ä", "AE")
        normalized = normalized.replace("Ö", "OE").replace("Ü", "UE").replace("ß", "SS")
        return normalized

    def _persist_graph(self, case_id: str):
        """Persist graph nodes and edges to database"""
        import json

        # Clear existing
        existing_nodes = self.session.exec(
            select(IdentityNode).where(IdentityNode.case_id == case_id)
        ).all()
        for n in existing_nodes:
            self.session.delete(n)

        existing_edges = self.session.exec(
            select(IdentityEdge).where(IdentityEdge.case_id == case_id)
        ).all()
        for e in existing_edges:
            self.session.delete(e)

        # Insert nodes
        node_id_map = {}  # GraphNode.id -> IdentityNode.id
        for gnode in self.nodes.values():
            props_str = json.dumps(gnode.properties) if isinstance(gnode.properties, dict) else str(gnode.properties)
            inode = IdentityNode(
                case_id=case_id,
                node_type=gnode.node_type,
                entity_id=gnode.entity_id,
                label=gnode.label,
                properties=props_str,
                confidence=gnode.confidence,
            )
            self.session.add(inode)
            self.session.flush()
            node_id_map[gnode.id] = inode.id

        # Insert edges
        for gedge in self.edges:
            if gedge.source in node_id_map and gedge.target in node_id_map:
                props_str = json.dumps(gedge.properties) if isinstance(gedge.properties, dict) else str(gedge.properties)
                ev_str = json.dumps(gedge.evidence_ids) if isinstance(gedge.evidence_ids, (list, tuple)) else str(gedge.evidence_ids)
                iedge = IdentityEdge(
                    case_id=case_id,
                    source_node_id=node_id_map[gedge.source],
                    target_node_id=node_id_map[gedge.target],
                    edge_type=gedge.edge_type,
                    weight=gedge.weight,
                    properties=props_str,
                    evidence_atom_ids=ev_str,
                    confidence=gedge.weight,  # Use weight as confidence
                )
                self.session.add(iedge)

        self.session.commit()



def build_identity_graph(case_id: str, session: Session) -> GraphSummary:
    """Convenience function"""
    builder = IdentityGraphBuilder(session)
    return builder.build(case_id)
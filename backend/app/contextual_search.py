"""
Contextual Search Service - Unified intelligent search engine
משלב בין חיפוש סמנטי, גרף קשרים והסברים טבעיים
"""
from typing import List, Dict, Optional
from app.semantic_service import SemanticSearchService
from app.graph_service import GraphService
from app.explanation_service import ExplanationService
from app.search_service import SearchService


class ContextualSearch:
    """
    מנוע חיפוש קונטקסטואלי חכם:
    משלב בין Embeddings, גרף קשרים והסברים טבעיים.
    
    Features:
    - Semantic search עם embeddings
    - Graph relationships (frontend ↔ backend)
    - Flow chains (HTML → JS → API → Backend)
    - Natural language explanations
    """
    
    def __init__(
        self, 
        search_service: SearchService,
        semantic_service: SemanticSearchService,
        graph_service: GraphService,
        explanation_service: ExplanationService
    ):
        self.search_service = search_service
        self.semantic_service = semantic_service
        self.graph_service = graph_service
        self.explanation_service = explanation_service
    
    def search(
        self, 
        query: str, 
        top_k: int = 10,
        include_related: bool = True,
        include_flow: bool = True,
        include_explanation: bool = True,
        depth: int = 2
    ) -> List[Dict]:
        """
        חיפוש קונטקסטואלי עם עומק הקשרי
        
        Args:
            query: שאילתת חיפוש
            top_k: מספר תוצאות מקסימלי
            include_related: האם לכלול קבצים קשורים
            include_flow: האם לכלול flow chains
            include_explanation: האם לכלול הסברים טבעיים
            depth: עומק הקשרים (1 = ישיר, 2 = עד רמה שנייה)
        
        Returns:
            רשימת תוצאות עם הקשר מלא
        """
        # שלב 1: חיפוש סמנטי בסיסי
        base_results = self._get_base_results(query, top_k)
        
        if not base_results:
            return []
        
        # שלב 2: הוספת הקשר לכל תוצאה
        contextual_results = []
        
        for result in base_results:
            contextual_result = {
                "base": result,
                "score": result.get("score", 0),
                "file_path": result.get("file_path", ""),
                "name": result.get("name", result.get("full_name", "")),
                "type": result.get("type", "code"),
                "language": result.get("language", ""),
                "code": result.get("code", result.get("content", "")),
                "start_line": result.get("start_line", result.get("line_number")),
                "end_line": result.get("end_line")
            }
            
            # הוספת קבצים קשורים
            if include_related:
                related = self._get_related_files(result, depth)
                contextual_result["related"] = related
                contextual_result["related_count"] = len(related)
            
            # הוספת flow chains
            if include_flow:
                flow_data = self._get_flow_data(result)
                contextual_result["flow"] = flow_data
            
            # הוספת הסבר טבעי
            if include_explanation:
                explanation = self._get_explanation(result, contextual_result.get("related", []))
                contextual_result["explanation"] = explanation
            
            contextual_results.append(contextual_result)
        
        return contextual_results
    
    def _get_base_results(self, query: str, top_k: int) -> List[Dict]:
        """קבלת תוצאות בסיסיות מחיפוש היברידי"""
        try:
            # נסה חיפוש היברידי
            if hasattr(self.search_service, 'hybrid_search'):
                results = self.search_service.hybrid_search(
                    query, 
                    max_results=top_k,
                    adaptive=True
                )
                if results:
                    return results
            
            # Fallback לחיפוש סמנטי
            if hasattr(self.semantic_service, 'semantic_search'):
                results = self.semantic_service.semantic_search(query, top_k=top_k)
                if results:
                    return results
            
            # Fallback לחיפוש רגיל
            if hasattr(self.search_service, 'search'):
                results = self.search_service.search(query, max_results=top_k)
                return results
            
            return []
        except Exception as e:
            print(f"Error in base search: {e}")
            return []
    
    def _get_related_files(self, base_result: Dict, depth: int = 2) -> List[Dict]:
        """קבלת קבצים קשורים דרך graph service"""
        try:
            related = self.graph_service.find_related(base_result)
            
            # סינון ומיון לפי חוזק קשר
            filtered_related = []
            for rel in related:
                # הוסף רק קבצים עם קשרים חזקים או בינוניים
                strength = rel.get("relation_strength", "weak")
                if strength in ["strong", "medium"]:
                    filtered_related.append({
                        "file_path": rel.get("file_path", ""),
                        "name": rel.get("name", ""),
                        "type": rel.get("type", ""),
                        "relation_type": rel.get("relation_type", "related"),
                        "relation_strength": strength,
                        "direction": rel.get("direction", ""),
                        "start_line": rel.get("start_line"),
                        "context": rel.get("context", "")
                    })
            
            # מיון לפי חוזק (strong → medium → weak)
            strength_order = {"strong": 3, "medium": 2, "weak": 1}
            filtered_related.sort(
                key=lambda x: strength_order.get(x.get("relation_strength", "weak"), 0),
                reverse=True
            )
            
            return filtered_related[:15]  # Limit to top 15
        except Exception as e:
            print(f"Error getting related files: {e}")
            return []
    
    def _get_flow_data(self, base_result: Dict) -> Dict:
        """קבלת flow graph עבור תוצאה"""
        try:
            # בנה flow graph מהתוצאה
            file_path = base_result.get("file_path", "")
            name = base_result.get("name", "")
            
            # חפש flow chains שמכילים את הקובץ הזה
            flow_chains = []
            
            # נסה לבנות flow graph מהתוצאה
            if hasattr(self.graph_service, 'build_flow_graph'):
                # השתמש בשם הקובץ כשאילתה
                query = f"{file_path} {name}"
                flow_graph = self.graph_service.build_flow_graph(query)
                
                # מצא chains שמכילים את הקובץ הזה
                chains = flow_graph.get("flow_chains", [])
                for chain in chains:
                    chain_str = " → ".join(chain)
                    if file_path in chain_str or name in chain_str:
                        flow_chains.append(chain)
            
            return {
                "flow_chains": flow_chains[:5],  # Limit to top 5 chains
                "has_flow": len(flow_chains) > 0
            }
        except Exception as e:
            print(f"Error getting flow data: {e}")
            return {"flow_chains": [], "has_flow": False}
    
    def _get_explanation(self, base_result: Dict, related: List[Dict]) -> str:
        """קבלת הסבר טבעי עבור תוצאה"""
        try:
            if hasattr(self.explanation_service, 'explain_flow'):
                explanation = self.explanation_service.explain_flow(base_result, related)
                return explanation
            
            # Fallback: הסבר בסיסי
            file_path = base_result.get("file_path", "")
            name = base_result.get("name", "")
            result_type = base_result.get("type", "code")
            
            explanation = f"Found {result_type} '{name}' in {file_path}"
            
            if related:
                explanation += f" with {len(related)} related components"
            
            return explanation
        except Exception as e:
            print(f"Error getting explanation: {e}")
            return ""
    
    def search_with_flow(self, query: str, top_k: int = 5) -> Dict:
        """
        חיפוש עם focus על flow chains (HTML → JS → API → Backend)
        
        Returns:
            Dictionary with base results and complete flow chains
        """
        # חיפוש בסיסי
        base_results = self._get_base_results(query, top_k)
        
        # בנה flow graph מלא
        flow_graph = None
        if hasattr(self.graph_service, 'build_flow_graph'):
            flow_graph = self.graph_service.build_flow_graph(query)
        
        return {
            "query": query,
            "results": base_results,
            "flow_graph": flow_graph or {},
            "total_results": len(base_results)
        }


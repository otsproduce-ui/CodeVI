"""
Graph Service - Adapter for graph processing
"""
class GraphService:
    """Simple adapter for graph processing"""
    def __init__(self, search_service):
        self.search_service = search_service

    def get_graph_data(self):
        """Get graph data from search service"""
        return self.search_service.get_graph()


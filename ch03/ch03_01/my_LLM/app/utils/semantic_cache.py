import time
from datetime import datetime

from chromadb import PersistentClient

class SemanticCache:
    # for customized collection for each user
    def __init__(self, collectionName='default_collection'):
        print('SemanticCache.__init__().collectionName:', collectionName)
        self.chromaClient = PersistentClient(path='app/chromadb/save')
        self.semanticCache = self.chromaClient.create_collection(name=collectionName, get_or_create=True)
        self.SECONDS_IN_WEEK = 7*24*60*60

    def addToCache(self, query, response):
        currentTimestamp = int(time.time())
        metadatas = {"response": response, "timestamp": currentTimestamp}
        self.semanticCache.add(documents=[query], metadatas=[metadatas], ids=[query])

    def queryToCache(self, query):
        oneWeekAgo = int(time.time()) - self.SECONDS_IN_WEEK

        results = self.semanticCache.get(ids=[query])   # exact match
        print('semanticCache.semanticCache.get(ids=[{}]).results: {}'.format(query, results))

        value = None

        if len(results["documents"]) > 0:
            print('self.semanticCache.get.results: {}'.format('exact match.'))
            value = {"distance": 0, "response": results["metadatas"][0]["response"]}
        else:
            results = self.semanticCache.query(
                query_texts=[query]
                , n_results=1
                , where={"timestamp": {"$gte": oneWeekAgo}})    # similar match
            print('self.semanticCache.query(query_texts=[{}], n_results=1, where={{"timestamp": {{"$gte": {}}}}}).results: {}'.format(query, oneWeekAgo, results))

            if len(results["documents"]) > 0 and len(results["documents"][0]) > 0:
                print('self.semanticCache.get.results: {}'.format('similar match.'))
                value = {"distance": results["distances"][0][0], "response": results["metadatas"][0][0]["response"]}
            else:
                value = None

        print('semanticCache.queryToCache.value: {}'.format(value))

        self.__deleteOldSemantics(self.SECONDS_IN_WEEK)

        return value

    def __deleteOldSemantics(self, timeInSeconds):
        oneWeekAgo = int(time.time()) - timeInSeconds
        self.semanticCache.delete(where={"timestamp": {"$lt": oneWeekAgo}})

    def getCollectionInfo(self):
        """컬렉션의 상세 정보를 반환합니다."""
        try:
            results = self.semanticCache.get()
            print('semantic_cache.py.getCollectionInfo().result:', results)

            count = len(results["ids"]) if results["ids"] else 0
            
            # 최신 타임스탬프 확인
            latest_timestamp = 0
            latest_timestamp_readable = "N/A"
            if results["metadatas"]:
                timestamps = [meta["timestamp"] for meta in results["metadatas"]]
                latest_timestamp = max(timestamps) if timestamps else 0
                
                # Unix 타임스탬프를 사람이 읽기 쉬운 형식으로 변환
                if latest_timestamp > 0:
                    dt = datetime.fromtimestamp(latest_timestamp)
                    latest_timestamp_readable = dt.strftime("%Y%m%d-%H%M%S")
            
            return {
                "total_records": count,
                "latest_timestamp": latest_timestamp,
                "latest_timestamp_YMDHMS": latest_timestamp_readable,
                "collection_name": self.semanticCache.name
            }
        except Exception as e:
            print(f"Error getting collection info: {e}")
            return {
                "total_records": 0, 
                "latest_timestamp": 0, 
                "latest_timestamp_YMDHMS": "N/A",
                "collection_name": "unknown"
            }

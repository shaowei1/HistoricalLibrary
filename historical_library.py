import os
import json
import warnings
import threading
from elasticsearch import Elasticsearch

ELASTIC_PASSWORD = "yangxinyue"
ES_INDEX = 'history_source'
semaphore = threading.Semaphore(12)


class EsFeeder:
    URL = 'https://localhost:9200'

    def __init__(self):
        self.client = Elasticsearch(self.URL,
                                    basic_auth=("elastic", ELASTIC_PASSWORD),
                                    verify_certs=False)

    def feed_one(self, json_data):
        semaphore.acquire()
        self.client.index(index=ES_INDEX, body=json_data, refresh=True)
        semaphore.release()

    def run(self, file_name):
        print(f"Processing #{file_name}")
        ts = [threading.Thread(target=self.feed_one, args=(j,)) for j in json.loads(open(file_name, 'r').read())]
        for t in ts:
            t.start()
            t.join()
        print("program terminated")

    def doc_count(self, file_name):
        return len(json.loads(open(file_name, 'r').read()))

    def delete_source(self, source):
        self.client.delete_by_query(
            index=ES_INDEX,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {"source": source}
                            }
                        ]
                    }
                }
            }
        )

    def delete_all(self):
        self.client.delete_by_query(
            index=ES_INDEX,
            body={
                "query": {
                    "match_all": {}
                }
            }
        )

    def count_by_source(self, source):
        return self.client.count(
            index=ES_INDEX,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match_phrase": {
                                    'source.keyword': {
                                        "query": source
                                    }
                                }
                            }
                        ]
                    }
                }
            },
            ignore=[404]
        ).get("count")

    def ingest_all(self):
        for file_name in os.listdir("./json"):
            self.run(f"./json/{file_name}")

    def post_run_test(self):
        for file_name in os.listdir("./json"):
            source = file_name.strip(".json")
            print(source)
            local_count = self.doc_count(f"./json/{file_name}")
            es_count = self.count_by_source(source)
            if es_count != local_count:
                print(f"Error: #{source} ingestion incomplete.Expected: #{local_count}. Actual: #{es_count}")
            else:
                print(f"{source} ingestion is sucessful")


def main():
    es_feeder = EsFeeder()

    warnings.filterwarnings("ignore")
    # Ingest one source
    # es_feeder.run('json/宋史.json')

    # Count local doc and elasticsearch doc
    # print(es_feeder.doc_count('json/宋史.json'))
    # print(es_feeder.count_by_source('宋史'))

    # Delete one souce
    # print(es_feeder.delete_source('宋史'))

    # Ingest all sources
    es_feeder.ingest_all()

    # Delete all sources
    # print(es_feeder.delete_all())

    # Test if any document missing
    es_feeder.post_run_test()


if __name__ == '__main__':
    main()

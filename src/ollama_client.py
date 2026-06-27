import requests

from src.vector_store import VectorStore
from src.embedding import EmbeddingManager
from src.retriever import RAGRetriever
from src.prompt_builder import PromptBuilder

class LLMGenerator:

    def __init__(
            self,
            model: str = "llama3.2",
            host: str = "http://localhost:11434"
    ):

        self.model = model
        self.host = host

        print("Loading Vector Store...")
        self.vector_store = VectorStore()

        print("Loading Embedding Model...")
        self.embedding_manager = EmbeddingManager()

        print("Initializing Retriever...")
        self.retriever = RAGRetriever(

            self.vector_store,

            self.embedding_manager

        )


    def generate(self, question: str,top_k: int = 2) -> str:


        print("\nRetrieving Relevant Documents...\n")

        docs = self.retriever.retrieve(question,top_k=top_k)


        if len(docs) == 0:

            return "No relevant lesson materials found."


        context = ""

        for doc in docs:


            context += f"""

Retrieved Passage (Score: {doc['similarity_score']:.3f})

{doc['content']}

------------------------------------------------------------

"""


        prompt = PromptBuilder.build(context=context,question=question)


        response = requests.post(

            f"{self.host}/api/chat",

            json={

                "model": self.model,

                "messages": [

                    {

                        "role": "user",

                        "content": prompt

                    }

                ],

                "stream": False

            }

        )


        return response.json()['message']['content']


if __name__ == "__main__":


    generator = LLMGenerator(

        model="llama3.2"

    )


    while True:


        question = input("\nAsk French Question (q to quit): ")

        if question.lower() == "q":

            break

        answer = generator.generate(question)
        print("\n")
        print("=" * 80)
        print(answer)
        print("=" * 80)
        print()

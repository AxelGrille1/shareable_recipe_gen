from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings

from library.constants.folders import FOLDER_DOCS_RAG_SOURCES, FILE_ENV
from langchain_community.vectorstores.hanavector import HanaDB
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from library.data.data_store import load_docs_from_github, split_docs_into_chunks
from library.data.hana_db import get_connection_to_hana_db
from pathlib import Path
from dotenv import load_dotenv


# Function to delete the already existing documents from the table
def main():
    question = "How to create a sub account with the Terraform provider for SAP BTP?"

    # Load environment variables
    load_dotenv(dotenv_path=str(FILE_ENV), verbose=True)

    # -------------------------------------------------------------------------------------
    # Load the documents into the HANA DB to get them vectorized
    # -------------------------------------------------------------------------------------

    # Load the documents from a GitHub repository
    repo_url = "https://github.com/SAP/terraform-provider-btp.git"
    repo_source_path = "docs"
    tf_source_path = Path(FOLDER_DOCS_RAG_SOURCES, "tf_provider_btp").resolve()
    tf_docs_all = load_docs_from_github(
        repo_url=repo_url, repo_source_path=repo_source_path, target_path=tf_source_path
    )

    # Split the documents into chunks
    chunks = split_docs_into_chunks(documents=tf_docs_all)

    # Get the connection to the HANA DB
    connection_to_hana = get_connection_to_hana_db()
    print("Connection to HANA DB established")

    # Get the proxy client for the AI Core service
    proxy_client = get_proxy_client("gen-ai-hub")
    # Create the OpenAIEmbeddings object
    embeddings = OpenAIEmbeddings(
        proxy_model_name="text-embedding-ada-002", proxy_client=proxy_client
    )
    print("OpenAIEmbeddings object created")
    llm = ChatOpenAI(proxy_model_name="gpt-35-turbo", proxy_client=proxy_client)
    print("ChatOpenAI object created")

    # Create a memory instance to store the conversation history
    memory = ConversationBufferMemory(
        memory_key="chat_history", output_key="answer", return_messages=True
    )

    print("Memory object created")

    # Create the HanaDB object
    db = HanaDB(
        embedding=embeddings, connection=connection_to_hana, table_name="TERRAFORM_DOCS"
    )
    print("HanaDB object created")

    # Delete already existing documents from the table
    db.delete(filter={})
    print("Deleted already existing documents from the table")

    # add the loaded document chunks to the HANA DB
    db.add_documents(chunks)
    print("Added the loaded document chunks to the HANA DB")

    # -------------------------------------------------------------------------------------
    # Fetch the data from the HANA DB and use it to answer the question using the
    # best 2 matching information chunks
    # -------------------------------------------------------------------------------------

    # Create a retriever instance of the vector store
    retriever = db.as_retriever(search_kwargs={"k": 2})
    print("Retriever instance of the vector store created")

    # -------------------------------------------------------------------------------------
    # Call the LLM with the RAG information retrieved from the HANA DB
    # -------------------------------------------------------------------------------------

    # Create prompt template
    prompt_template = """
    You are a helpful assistant. You are provided multiple context items that are related to the prompt you have to answer.
    Use the following pieces of context to answer the question at the end. If the answer is not in the context, reply exactly with "I don't know".

    ```
    {context}
    ```

    Question: {question}
    """

    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    chain_type_kwargs = {"prompt": PROMPT}

    # Create a conversational retrieval chain
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm,
        retriever,
        return_source_documents=True,
        memory=memory,
        verbose=False,
        combine_docs_chain_kwargs=chain_type_kwargs,
    )

    # -------------------------------------------------------------------------------------
    # Provide the response to the user
    # -------------------------------------------------------------------------------------

    print("Conversational retrieval chain created")

    print("Asking a question:", question)

    result = qa_chain.invoke({"question": question})
    print("Answer from LLM:")
    print(result["answer"])

    source_docs = result["source_documents"]

    print(f"Number of used source document chunks: {len(source_docs)}")
    for doc in source_docs:
        print(doc.page_content)


if __name__ == "__main__":
    main()

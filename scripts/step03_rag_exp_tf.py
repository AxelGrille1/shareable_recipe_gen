from firebase_admin import credentials, initialize_app, firestore
import json
import time
import random
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings

from library.constants.folders import FOLDER_DOCS_RAG_SOURCES, FILE_ENV
from langchain_community.vectorstores.hanavector import HanaDB
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from library.data.data_store import load_docs, split_docs_into_chunks
from library.data.hana_db import get_connection_to_hana_db
from pathlib import Path
from dotenv import load_dotenv
import time
import math

def main(input, uuid):
    start = time.time()
    question = f"You are an industrial recipe formulator. Generate recipes with industrial recipe steps from {input} based on the recipes in the database, the result is a JSON containing the following fields: allergens, ingredients, price, recipe, pieces, sustainability_index, nutrients, UUID: {uuid}, recipe name. Number the recipe steps with closing parentheses and return them as a single string using the special newline character. Give each recipe an original name. Enter ingredients as a single string, in liters and kilograms, and no more than 6 ingredients. Leave the sources field blank. Generate a sustainability score from 1 to 5 in the sustainability_index field, I just want a number in a string field. Include an empty price field. Finally, list the proteins, fats and carbohydrates for each recipe in the nutrients field as a single string. Indicate all quantities in grams and temperatures in degrees Celsius. Convert quantities for 100kg or 100L, do not change proportions. Return a single recipe. The id field must be named 'UUID'. The response must be formatted in JSON, it must absolutely be a class dict and nothing else. NO YAPPING. Don't add any comments, start the response with a bracket and end it with a closing bracket"



    # Load environment variables
    load_dotenv(dotenv_path=str(FILE_ENV), verbose=True)

    # -------------------------------------------------------------------------------------
    # Load the documents into the HANA DB to get them vectorized
    # -------------------------------------------------------------------------------------

    # Load the documents
    tf_docs_all = load_docs(
        tf_source_path=Path(FOLDER_DOCS_RAG_SOURCES, "tf_provider_btp").resolve()
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
    llm = ChatOpenAI(proxy_model_name="gpt-4-32k", proxy_client=proxy_client)
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
    # db.delete(filter={})
    # print("Deleted already existing documents from the table")

    # add the loaded document chunks to the HANA DB
    # db.add_documents(chunks)
    # print("Added the loaded document chunks to the HANA DB")

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
    Use the following pieces of context to answer the question at the end.".

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
        combine_docs_chain_kwargs=chain_type_kwargs
    )

    # -------------------------------------------------------------------------------------
    # Provide the response to the user
    # -------------------------------------------------------------------------------------

    print("Conversational retrieval chain created")

    print("Asking a question:", question)

    result = qa_chain.invoke({"question": question})
    print("Answer from LLM:")
    # print(result["answer"])
    # print(type(result["answer"]))

    source_docs = result["source_documents"]

    sources = []

    print(f"Number of used source document chunks: {len(source_docs)}")
    for doc in source_docs:
        buff = doc.page_content
        sources.append(buff)
        print(doc.page_content)


    end = time.time()

    elapsed = end - start

    print(elapsed)
    minutes = math.floor(elapsed / 60)
    seconds = elapsed % 60
    print(f"Total execution time: {minutes} minutes and {seconds:.2f} seconds")

    return result["answer"], sources

if __name__ == "__main__":
    main()

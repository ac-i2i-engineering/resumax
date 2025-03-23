from huggingface_hub import login
from langchain_huggingface import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig, pipeline, BitsAndBytesConfig
import torch
from textwrap import fill
from langchain.prompts import PromptTemplate
import locale
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
import logging
import os
locale.getpreferredencoding = lambda: "UTF-8"

# from huggingface_hub import login
from resumax_backend.settings import BASE_DIR,HUGGINGFACE_TOKEN, DEBUG
login(HUGGINGFACE_TOKEN)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
VECTOR_STORE_PATH = os.path.join(BASE_DIR, "vectordb")
EMBEDDING_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
LLM_MODEL_NAME = "meta-llama/Llama-3.2-1B-Instruct"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SCORE_THRESHOLD = 0.2


def load_embeddings(embedding_model_name=EMBEDDING_MODEL_NAME, device=DEVICE):
    """Loads HuggingFace embeddings."""
    model_kwargs = {"device": device}
    if DEBUG:
        logging.info(f"Using device: {device}")
    return HuggingFaceEmbeddings(
        model_name=embedding_model_name,
        model_kwargs=model_kwargs,
        multi_process=False,
    )


def load_vector_store(save_directory, embeddings):
    """Loads FAISS vector store from local directory."""
    try:
        vector_store = FAISS.load_local(save_directory, embeddings, allow_dangerous_deserialization=True)
        if DEBUG:
            logging.info(f"Successfully loaded vector store from {save_directory}")
        return vector_store
    except Exception as e:
        logging.error(f"Error loading vector store: {e}")
        return None


def load_llm(model_name=LLM_MODEL_NAME, device=DEVICE):
    """Loads language model and tokenizer."""
    if device == "cuda":
        quantization_config = BitsAndBytesConfig()
        model = AutoModelForCausalLM.from_pretrained(model_name,
                                                     device_map=device,
                                                     quantization_config=quantization_config,
                                                     trust_remote_code=True)
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
        )
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    return model, tokenizer


def create_pipeline(model, tokenizer, device=DEVICE):
    """Creates text generation pipeline."""
    gen_cfg = GenerationConfig.from_pretrained(LLM_MODEL_NAME)
    gen_cfg.max_new_tokens = 512
    gen_cfg.temperature = 0.0000001
    gen_cfg.return_full_text = True
    gen_cfg.do_sample = True
    gen_cfg.repetition_penalty = 1.11

    pipe = pipeline(
        task="text-generation",
        model=model,
        tokenizer=tokenizer,
        generation_config=gen_cfg,
        device=device  # Ensure pipeline uses the correct device
    )
    return HuggingFacePipeline(pipeline=pipe)


def create_prompt_template():
    """Creates prompt template for resume review."""
    prompt_template_llama3 = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    You are a resume reviewer. You will be given a resume. Use the following context to answer the question and give tailored feedback
    on how to improve the resume. Be concise and to the point. Return in this format:

    <general review of the resume>
    [The text of the general review]
    </general review of the resume>

    <tailored feedback answering the question>
    [The text of the tailored feedback]
    </tailored feedback>

    <Next steps for improvement>
    [The text of the next steps for improvement]
    </Next steps for improvement>

    {context}<|eot_id|><|start_header_id|>user<|end_header_id|>

    {question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """
    return PromptTemplate(template=prompt_template_llama3, input_variables=["context", "question"])


def create_retrieval_qa_chain(llm, vector_store, prompt, score_threshold=SCORE_THRESHOLD):
    """Creates retrieval QA chain."""
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_type="similarity_score_threshold",
                                            search_kwargs={'k': 10, 'score_threshold': score_threshold}),
        chain_type_kwargs={"prompt": prompt},
    )


def generate_content(qa_chain, query):
    """Generates content based on the query."""
    try:
        result = qa_chain.invoke(query)
        clean_result = result['result'].split("<|eot_id|><|start_header_id|>assistant<|end_header_id|>")[-1].strip()
        return clean_result
    except Exception as e:
        logging.warning("No relevant docs were retrieved using the relevance score threshold.")
        return "I'm sorry, but I am not trained for that kind of task. Please try a different query."


def generate_response(query):
    # Load resources
    embeddings = load_embeddings()
    vector_store = load_vector_store(VECTOR_STORE_PATH, embeddings)

    if vector_store is None:
        logging.error("Failed to load vector store. Exiting.")
        return "Failed to load vector store."
    else:
        model, tokenizer = load_llm()
        llm = create_pipeline(model, tokenizer)
        prompt = create_prompt_template()
        qa_chain = create_retrieval_qa_chain(llm, vector_store, prompt)

        # Example usage
        response = generate_content(qa_chain, query)
        return fill(response, width=200)
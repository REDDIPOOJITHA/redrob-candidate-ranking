"""
parse_jd.py
JD requirements as structured config — no file I/O during ranking.
"""

JD_TEXT = """
Senior AI Engineer Founding Team Redrob AI Series A
Location Pune Noida India five to nine years experience
Production embeddings retrieval ranking LLMs sentence-transformers
OpenAI embeddings BGE E5 vector databases Pinecone Weaviate Qdrant Milvus
OpenSearch Elasticsearch FAISS strong Python evaluation NDCG MRR MAP
recommendation ranking retrieval search recommender matching vector database
embeddings semantic search dense retrieval production deployment
product company not services TCS Infosys Wipro Accenture Cognizant
LLM fine-tuning LoRA QLoRA PEFT learning to rank XGBoost
""".strip()

MUST_HAVE_SKILLS = {
    "python", "embeddings", "retrieval", "ranking", "vector database",
    "sentence-transformers", "faiss", "pinecone", "weaviate", "qdrant",
    "milvus", "opensearch", "elasticsearch", "llm", "nlp",
    "machine learning", "recommendation", "search", "rag",
    "ndcg", "mrr", "information retrieval",
}

NICE_TO_HAVE_SKILLS = {
    "lora", "qlora", "peft", "fine-tuning", "xgboost",
    "learning to rank", "distributed systems", "pytorch",
    "tensorflow", "transformers", "hugging face", "open source",
}

PRODUCT_COMPANIES = [
    "amazon", "google", "microsoft", "meta", "apple", "netflix",
    "flipkart", "swiggy", "zomato", "uber", "ola", "paytm",
    "razorpay", "phonepe", "cred", "meesho", "myntra", "nykaa",
    "freshworks", "zoho", "atlassian", "stripe", "airbnb",
    "redrob", "startup",
]

SERVICE_COMPANIES = [
    "tcs", "infosys", "wipro", "cognizant", "capgemini",
    "accenture", "hcl", "tech mahindra", "mphasis", "hexaware",
    "mindtree", "ltimindtree",
]

DISQUALIFYING_TITLES = {
    "marketing", "sales", "hr ", "human resource", "legal",
    "finance", "accounting", "recruiter", "content writer",
    "journalist", "graphic designer",
}

PREFERRED_LOCATIONS = {
    "pune", "noida", "hyderabad", "mumbai", "delhi", "bangalore",
    "bengaluru", "gurgaon", "gurugram", "india", "ncr",
}

import redivis

user = redivis.user("zw3155")
dataset = user.dataset("coms6901_email_dataset_original_repo_output:e83c:v1_0")
table = dataset.table("normalized_dataset:a8hm")

# Load table as a dataframe
df = table.to_pandas_dataframe(max_results=100)
df.head()

from pymongo import MongoClient

# Replace with your actual MongoDB connection string
MONGO_URI = "mongodb+srv://deepakmuvvala:F2qCPJBBGk3l9McI@cluster.0uf8v.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"

def get_db():
    client = MongoClient(MONGO_URI)
    return client['crud_db']  # Replace with your actual database name

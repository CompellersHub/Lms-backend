import os
import requests
from pymongo import MongoClient
import json
from bson import ObjectId
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_mongo_collections():
    """Get all collections from your MongoDB database"""
    MONGO_URI = os.getenv('MONGO_URI')
    DATABASE_NAME = os.getenv('DATABASE_NAME')
    
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    
    collections = db.list_collection_names()
    print("Available collections:", collections)
    return db, collections

def migrate_all_collections():
    """Migrate all collections from MongoDB to Supabase"""
    
    # Get MongoDB connection
    db, collections = get_mongo_collections()
    
    # Supabase configuration
    SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
    SUPABASE_KEY = os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY")
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # Migrate each collection
    for collection_name in collections:
        print(f"\n{'='*50}")
        print(f"Migrating collection: {collection_name}")
        print(f"{'='*50}")
        
        migrate_single_collection(db, collection_name, SUPABASE_URL, headers)

def migrate_single_collection(db, collection_name, supabase_url, headers):
    """Migrate a single collection to Supabase"""
    
    collection = db[collection_name]
    
    # Get all documents
    documents = list(collection.find())
    total_docs = len(documents)
    
    print(f"Found {total_docs} documents in {collection_name}")
    
    if total_docs == 0:
        print("No documents to migrate")
        return
    
    successful = 0
    failed_docs = []
    
    for i, doc in enumerate(documents):
        try:
            # Transform document for Supabase
            transformed_doc = transform_document(doc, collection_name)
            
            # Insert into Supabase (using collection name as table name)
            response = requests.post(
                f"{supabase_url}/rest/v1/{collection_name}",
                headers=headers,
                json=transformed_doc,
                timeout=30
            )
            
            if response.status_code in [200, 201, 204]:
                successful += 1
            else:
                failed_docs.append({
                    'document_id': str(doc.get('_id', 'unknown')),
                    'error': f"HTTP {response.status_code}: {response.text}"
                })
            
            # Progress reporting
            if (i + 1) % 100 == 0 or (i + 1) == total_docs:
                print(f"Progress: {i + 1}/{total_docs} ({successful} successful)")
            
            # Small delay to avoid rate limiting
            time.sleep(0.01)
            
        except Exception as e:
            failed_docs.append({
                'document_id': str(doc.get('_id', 'unknown')),
                'error': str(e)
            })
    
    # Summary for this collection
    print(f"\n=== {collection_name} Migration Summary ===")
    print(f"Total documents: {total_docs}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(failed_docs)}")
    
    # Save failed documents for this collection
    if failed_docs:
        filename = f"failed_{collection_name}.json"
        with open(filename, 'w') as f:
            json.dump(failed_docs, f, indent=2, default=str)
        print(f"Failed documents saved to {filename}")

def transform_document(doc, collection_name):
    """Transform MongoDB document for Supabase"""
    transformed = {}
    
    for key, value in doc.items():
        # Skip some MongoDB internal fields if needed
        if key in ['__v']:  # Common Mongoose field
            continue
            
        # Handle _id field
        if key == '_id':
            transformed['id'] = str(value)
        # Handle ObjectId in nested fields
        elif isinstance(value, ObjectId):
            transformed[key] = str(value)
        # Handle dates
        elif isinstance(value, datetime):
            transformed[key] = value.isoformat()
        # Handle nested documents and arrays
        elif isinstance(value, (dict, list)):
            transformed[key] = json.dumps(serialize_complex_types(value), default=str)
        # Handle other types
        else:
            transformed[key] = value
    
    # Add metadata
    transformed['_migrated_at'] = datetime.now().isoformat()
    transformed['_source_collection'] = collection_name
    
    return transformed

def serialize_complex_types(obj):
    """Recursively serialize complex types for JSON"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_complex_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_complex_types(item) for item in obj]
    else:
        return obj

def check_collection_stats():
    """Check what's in your MongoDB database"""
    db, collections = get_mongo_collections()
    
    print("\n=== Database Overview ===")
    for collection_name in collections:
        collection = db[collection_name]
        count = collection.count_documents({})
        # Get sample document to understand structure
        sample = collection.find_one()
        print(f"\nCollection: {collection_name}")
        print(f"Document count: {count}")
        if sample:
            print("Sample document keys:", list(sample.keys())[:10])  # First 10 keys
            if count > 0:
                print("Sample _id:", sample.get('_id'))

if __name__ == "__main__":
    # First, let's see what collections you have
    check_collection_stats()
    
    # Ask user if they want to proceed with migration
    response = input("\nDo you want to proceed with migration? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        migrate_all_collections()
    else:
        print("Migration cancelled")
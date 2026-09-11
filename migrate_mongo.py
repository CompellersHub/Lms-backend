import os
import requests
from pymongo import MongoClient
import json
from bson import ObjectId
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_mongo_collections():
    """Get all collections from your MongoDB database"""
    MONGO_URI = os.getenv('MONGO_URI')
    DATABASE_NAME = os.getenv('DATABASE_NAME')
    
    print("Connecting to MongoDB...")
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    
    collections = db.list_collection_names()
    print(f"Connected to database: {DATABASE_NAME}")
    print("Available collections:", collections)
    return db, collections

def check_collection_stats():
    """Check what's in your MongoDB database"""
    db, collections = get_mongo_collections()
    
    print("\n" + "="*60)
    print("DATABASE OVERVIEW")
    print("="*60)
    
    for collection_name in collections:
        collection = db[collection_name]
        count = collection.count_documents({})
        # Get sample document to understand structure
        sample = collection.find_one()
        print(f"\n📁 Collection: {collection_name}")
        print(f"   📊 Document count: {count}")
        if sample:
            print(f"   🔑 Sample keys: {list(sample.keys())[:8]}")  # First 8 keys
            if count > 0:
                print(f"   🆔 Sample _id: {sample.get('_id')}")
    
    return collections

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
    
    # Add migration metadata
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

def migrate_single_collection(db, collection_name, supabase_url, supabase_key):
    """Migrate a single collection to Supabase"""
    
    collection = db[collection_name]
    
    # Get all documents
    documents = list(collection.find())
    total_docs = len(documents)
    
    print(f"📦 Found {total_docs} documents in '{collection_name}'")
    
    if total_docs == 0:
        print("   ⚠️ No documents to migrate")
        return
    
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,  
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    successful = 0
    failed_docs = []
    
    print("   🚀 Starting migration...")
    
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
                if len(failed_docs) <= 3:  # Print first few errors
                    print(f"   ❌ Failed document {doc.get('_id')}: {response.status_code}")
            
            # Progress reporting
            if (i + 1) % 100 == 0 or (i + 1) == total_docs:
                print(f"   📈 Progress: {i + 1}/{total_docs} ({successful} successful)")
            
            # Small delay to avoid rate limiting
            time.sleep(0.01)
            
        except Exception as e:
            failed_docs.append({
                'document_id': str(doc.get('_id', 'unknown')),
                'error': str(e)
            })
            if len(failed_docs) <= 3:  # Print first few exceptions
                print(f"   💥 Exception on document {doc.get('_id')}: {e}")
    
    # Summary for this collection
    print(f"\n   ✅ {collection_name} Migration Summary:")
    print(f"      Total documents: {total_docs}")
    print(f"      Successful: {successful}")
    print(f"      Failed: {len(failed_docs)}")
    
    # Save failed documents for this collection
    if failed_docs:
        filename = f"failed_{collection_name}.json"
        with open(filename, 'w') as f:
            json.dump(failed_docs, f, indent=2, default=str)
        print(f"      📄 Failed documents saved to {filename}")
    
    return successful, len(failed_docs)

def migrate_all_collections():
    """Migrate all collections from MongoDB to Supabase"""
    
    # Get MongoDB connection
    db, collections = get_mongo_collections()
    
    # Supabase configuration - UPDATE THESE!
    SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
    SUPABASE_KEY = os.getenv("VITE_SUPABASE_SERVICE_ROLE_KEY")  
    
    if SUPABASE_URL == "https://your-project-ref.supabase.co":
        print("\n❌ Please update SUPABASE_URL and SUPABASE_KEY in the script!")
        print("   Get these from Supabase dashboard: Settings > API")
        return
    
    print(f"\n🎯 Target Supabase: {SUPABASE_URL}")
    
    total_successful = 0
    total_failed = 0
    
    # Migrate each collection
    for collection_name in collections:
        print(f"\n{'='*60}")
        print(f"🚀 MIGRATING: {collection_name}")
        print(f"{'='*60}")
        
        successful, failed = migrate_single_collection(db, collection_name, SUPABASE_URL, SUPABASE_KEY)
        total_successful += successful
        total_failed += failed
    
    # Final summary
    print(f"\n{'='*60}")
    print("🎉 MIGRATION COMPLETE!")
    print(f"{'='*60}")
    print(f"📊 Total Successful: {total_successful}")
    print(f"📊 Total Failed: {total_failed}")
    print(f"🏁 Total Collections: {len(collections)}")

def main():
    """Main function with user interaction"""
    print("🔍 Checking your MongoDB database...")
    
    # First, show what we found
    collections = check_collection_stats()
    
    if not collections:
        print("❌ No collections found in the database!")
        return
    
    print(f"\n{'='*60}")
    print("🚀 MongoDB to Supabase Migrator")
    print(f"{'='*60}")
    print("This script will:")
    print("1. Connect to your MongoDB database")
    print("2. Read all collections and documents") 
    print("3. Transform the data for Supabase")
    print("4. Upload to your Supabase project")
    print(f"{'='*60}")
    
    # Check if Supabase credentials are set
    SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
    if SUPABASE_URL == "https://your-project-ref.supabase.co":
        print("\n📝 Before running, please:")
        print("   1. Create a Supabase project at https://supabase.com")
        print("   2. Get your Project URL and Service Role Key")
        print("   3. Update the SUPABASE_URL and SUPABASE_KEY in this script")
        print("\n   You can find these in Supabase: Settings > API")
        return
    
    response = input("\nDo you want to proceed with migration? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        migrate_all_collections()
    else:
        print("Migration cancelled")

if __name__ == "__main__":
    main()
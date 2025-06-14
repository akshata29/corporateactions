"""
Data ingestion script for Corporate Actions
Loads sample data into Azure Cosmos DB and Azure AI Search
"""

import asyncio
import json
import os
import sys
import platform
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import logging
import random

# Azure SDK imports
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.core.credentials import AzureKeyCredential
from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, ClientSecretCredential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Generate synthetic data
def generate_synthetic_events(count: int = 150) -> List[Dict[str, Any]]:
    """Generate synthetic corporate action events"""
    companies = [
        ("AAPL", "Apple Inc."), ("MSFT", "Microsoft Corporation"), ("GOOGL", "Alphabet Inc."),
        ("AMZN", "Amazon.com Inc."), ("TSLA", "Tesla Inc."), ("META", "Meta Platforms Inc."),
        ("NVDA", "NVIDIA Corporation"), ("JPM", "JPMorgan Chase & Co."), ("JNJ", "Johnson & Johnson"),
        ("V", "Visa Inc."), ("WMT", "Walmart Inc."), ("PG", "Procter & Gamble Co."),
        ("UNH", "UnitedHealth Group Inc."), ("HD", "Home Depot Inc."), ("MA", "Mastercard Inc."),
        ("BAC", "Bank of America Corp."), ("PFE", "Pfizer Inc."), ("DIS", "Walt Disney Co."),
        ("ADBE", "Adobe Inc."), ("CRM", "Salesforce Inc."), ("NFLX", "Netflix Inc."),
        ("XOM", "Exxon Mobil Corp."), ("VZ", "Verizon Communications"), ("CSCO", "Cisco Systems"),
        ("INTC", "Intel Corporation"), ("CVX", "Chevron Corporation"), ("TMO", "Thermo Fisher Scientific"),
        ("ABBV", "AbbVie Inc."), ("ACN", "Accenture PLC"), ("NKE", "Nike Inc."),
        ("COP", "ConocoPhillips"), ("LLY", "Eli Lilly and Co."), ("AVGO", "Broadcom Inc."),
        ("PM", "Philip Morris International"), ("TXN", "Texas Instruments"), ("QCOM", "Qualcomm Inc."),
        ("HON", "Honeywell International"), ("RTX", "Raytheon Technologies"), ("UPS", "United Parcel Service"),
        ("LOW", "Lowe's Companies"), ("IBM", "International Business Machines"), ("CAT", "Caterpillar Inc."),
        ("AXP", "American Express Co."), ("GS", "Goldman Sachs Group"), ("BLK", "BlackRock Inc."),
        ("SBUX", "Starbucks Corporation"), ("MDT", "Medtronic PLC"), ("BA", "Boeing Co."),
        ("AMGN", "Amgen Inc."), ("SPGI", "S&P Global Inc."), ("BKNG", "Booking Holdings Inc.")
    ]
    
    event_types = ["dividend", "stock_split", "merger", "spinoff", "special_dividend", "rights_offering"]
    statuses = ["announced", "confirmed", "processed", "cancelled"]
    
    events = []
    base_date = date(2024, 1, 1)
    
    for i in range(count):
        symbol, company_name = random.choice(companies)
        event_type = random.choice(event_types)
        status = random.choice(statuses)
        
        # Generate dates
        announcement_date = base_date + timedelta(days=random.randint(0, 365))
        record_date = announcement_date + timedelta(days=random.randint(10, 30))
        ex_date = record_date - timedelta(days=1)
        payment_date = record_date + timedelta(days=random.randint(7, 21))
        
        # Generate event details based on type
        event_details = {}
        if event_type == "dividend":
            event_details = {
                "dividend_amount": round(random.uniform(0.10, 2.50), 2),
                "currency": "USD",
                "frequency": random.choice(["quarterly", "annual", "semi-annual"])
            }
            description = f"${event_details['dividend_amount']} {event_details['frequency']} cash dividend"
        elif event_type == "stock_split":
            ratio = random.choice(["2:1", "3:1", "3:2", "4:1"])
            event_details = {
                "split_ratio": ratio,
                "new_shares_per_old": int(ratio.split(':')[0])
            }
            description = f"{ratio} stock split"
        elif event_type == "special_dividend":
            event_details = {
                "dividend_amount": round(random.uniform(1.00, 10.00), 2),
                "currency": "USD",
                "type": "special"
            }
            description = f"Special cash dividend of ${event_details['dividend_amount']} per share"
        else:
            description = f"{event_type.replace('_', ' ').title()} corporate action"
        
        event = {
            "event_id": f"{symbol}_{event_type.upper()}_{announcement_date.year}_{i:03d}",
            "event_type": event_type,
            "security": {
                "symbol": symbol,
                "cusip": f"{random.randint(100000000, 999999999)}",
                "isin": f"US{random.randint(1000000000, 9999999999)}"
            },
            "issuer_name": company_name,
            "announcement_date": announcement_date,
            "record_date": record_date,
            "ex_date": ex_date,
            "payable_date": payment_date,
            "status": status,
            "description": description,
            "event_details": event_details,
            "data_source": "GENERATED"
        }
        events.append(event)
    
    return events

def generate_synthetic_comments(events: List[Dict[str, Any]], count: int = 300) -> List[Dict[str, Any]]:
    """Generate synthetic comments for events"""
    users = ["trader_pro", "investor_123", "analyst_smith", "fund_manager", "retail_joe", "pension_admin"]
    comment_types = ["general", "question", "analysis", "clarification"]
    
    comments = []
    
    for i in range(count):
        event = random.choice(events)
        user = random.choice(users)
        comment_type = random.choice(comment_types)
        
        # Generate comment text based on type
        if comment_type == "question":
            comment_texts = [
                "What are the tax implications of this action?",
                "When will the payment be processed?",
                "How does this affect my holdings?",
                "What's the record date for this event?",
                "Are there any deadlines I need to be aware of?"
            ]
        elif comment_type == "analysis":
            comment_texts = [
                "This looks positive for long-term shareholders.",
                "The yield is quite attractive compared to peers.",
                "This split should improve liquidity.",
                "Strong balance sheet supports this dividend.",
                "Market reaction has been positive so far."
            ]
        else:
            comment_texts = [
                "Thanks for the update!",
                "Good news for shareholders.",
                "Will monitor this closely.",
                "Appreciate the transparency.",
                "Looking forward to the payment."
            ]
        
        comment = {
            "comment_id": f"comment_{i:06d}",
            "event_id": event["event_id"],
            "user_name": user,
            "comment_text": random.choice(comment_texts),
            "comment_type": comment_type,
            "created_at": datetime.utcnow() - timedelta(days=random.randint(0, 30)),
            "votes": random.randint(0, 15)
        }
        comments.append(comment)
    
    return comments

class DataIngestionService:
    """Service to ingest corporate actions data into Azure services"""
    
    def __init__(self):
        self.cosmos_client = None
        self.search_client = None
        self.search_index_client = None
        self.openai_client = None
        self.sample_events = generate_synthetic_events(150)
        self.sample_comments = generate_synthetic_comments(self.sample_events, 300)
                
    async def initialize_clients(self):
        """Initialize Azure service clients"""
        try:
            # Initialize Cosmos DB client
            cosmos_endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
            cosmos_key = os.getenv("AZURE_COSMOS_KEY")
            
            # service principal
            tenant_id = os.getenv('AZURE_TENANT_ID')
            client_id = os.getenv('AZURE_CLIENT_ID')
            client_secret = os.getenv('AZURE_CLIENT_SECRET')
            cred = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)

            if cosmos_endpoint:
                self.cosmos_client = CosmosClient(cosmos_endpoint, credential=cred)
                logger.info("Cosmos DB client initialized")
            else:
                logger.warning("Cosmos DB credentials not found")
            
            # Initialize AI Search clients
            search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
            search_key = os.getenv("AZURE_SEARCH_KEY")
            search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "corporate-actions")
            
            if search_endpoint and search_key:
                credential = AzureKeyCredential(search_key)
                self.search_client = SearchClient(
                    endpoint=search_endpoint,
                    index_name=search_index_name,
                    credential=credential
                )
                self.search_index_client = SearchIndexClient(
                    endpoint=search_endpoint,
                    credential=credential
                )
                logger.info("AI Search clients initialized")
            else:
                logger.warning("AI Search credentials not found")
            
            # Initialize Azure OpenAI client
            openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            openai_key = os.getenv("AZURE_OPENAI_KEY")
            
            if openai_endpoint and openai_key:
                self.openai_client = AsyncAzureOpenAI(
                    azure_endpoint=openai_endpoint,
                    api_key=openai_key
                    api_version="2024-02-15-preview"
                )
                logger.info("Azure OpenAI client initialized")
            else:
                logger.warning("Azure OpenAI credentials not found")
                
        except Exception as e:
            logger.error(f"Error initializing clients: {e}")
            raise
    
    async def setup_cosmos_db(self):
        """Setup Cosmos DB database and containers"""
        try:
            if not self.cosmos_client:
                logger.warning("Cosmos DB client not available, skipping setup")
                return
            
            database_name = os.getenv("AZURE_COSMOS_DATABASE_NAME", "semantickernel")
            logger.info(f"Setting up Cosmos DB database: {database_name}")
            
            # Create database
            database = await self.cosmos_client.create_database_if_not_exists(id=database_name)
            logger.info(f"Database '{database_name}' ready")
            
            # Create containers
            containers = [
                {
                    "id": "events",
                    "partition_key": "/event_id",
                    "default_ttl": -1  # No TTL
                },
                {
                    "id": "comments",
                    "partition_key": "/comment_id",
                    "default_ttl": -1  # No TTL
                }
            ]
            
            for container_config in containers:
                container = await database.create_container_if_not_exists(
                    id=container_config["id"],
                    partition_key=PartitionKey(path=container_config["partition_key"]),
                )
                logger.info(f"Container '{container_config['id']}' ready")
                
        except Exception as e:
            logger.error(f"Error setting up Cosmos DB: {e}")
            raise
    
    async def setup_search_index(self):
        """Setup Azure AI Search index"""
        try:
            if not self.search_index_client:
                logger.warning("Search index client not available, skipping setup")
                return
            
            index_name = "corporate-actions"
            
            # Define search index schema
            fields = [
                SimpleField(name="event_id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="event_type", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="issuer_name", type=SearchFieldDataType.String, searchable=True),
                SearchableField(name="description", type=SearchFieldDataType.String, searchable=True),
                SimpleField(name="symbol", type=SearchFieldDataType.String, filterable=True, searchable=True),
                SimpleField(name="cusip", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="status", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="announcement_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="record_date", type=SearchFieldDataType.DateTimeOffset, filterable=True),
                SimpleField(name="ex_date", type=SearchFieldDataType.DateTimeOffset, filterable=True),
                SimpleField(name="payable_date", type=SearchFieldDataType.DateTimeOffset, filterable=True),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_profile_name="my-vector-config"
                ),
                SearchableField(name="searchable_content", type=SearchFieldDataType.String, searchable=True)
            ]
            
            # Vector search configuration
            vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="my-vector-config",
                        algorithm_configuration_name="my-algorithms-config"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="my-algorithms-config"
                    )
                ]
            )
            
            # Create search index
            index = SearchIndex(
                name=index_name,
                fields=fields,
                vector_search=vector_search
            )
            
            result = await self.search_index_client.create_or_update_index(index)
            logger.info(f"Search index '{index_name}' created/updated")
            
        except Exception as e:
            logger.error(f"Error setting up search index: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text content"""
        try:
            if self.openai_client:
                response = await self.openai_client.embeddings.create(
                    input=text,
                    model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002")
                )
                return response.data[0].embedding
            else:
                # Return dummy embedding for testing
                import random
                return [random.random() for _ in range(1536)]
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return dummy embedding on error
            import random
            return [random.random() for _ in range(1536)]
    
    async def ingest_events_to_cosmos(self):
        """Ingest sample events to Cosmos DB"""
        try:
            if not self.cosmos_client:
                logger.warning("Cosmos DB client not available, skipping event ingestion")
                return
            
            database = self.cosmos_client.get_database_client(os.getenv("AZURE_COSMOS_DATABASE_NAME", "semantickernel"))
            container = database.get_container_client("events")
            
            for event_data in self.sample_events:
                # Convert date objects to ISO format strings
                processed_event = self._process_event_for_storage(event_data)
                
                logger.info(f"Ingesting event: {processed_event}")
                await container.upsert_item(processed_event)
                logger.info(f"Ingested event: {processed_event['event_id']}")
            
            logger.info(f"Successfully ingested {len(self.sample_events)} events to Cosmos DB")
            
        except Exception as e:
            logger.error(f"Error ingesting events to Cosmos DB: {e}")
            raise
    
    async def ingest_events_to_search(self):
        """Ingest sample events to Azure AI Search with vectors"""
        try:
            if not self.search_client:
                logger.warning("Search client not available, skipping search ingestion")
                return
            
            search_documents = []
            
            for event_data in self.sample_events:
                # Create searchable content
                searchable_content = self._create_searchable_content(event_data)
                
                # Generate embedding
                embedding = await self.generate_embedding(searchable_content)
                
                # Create search document
                search_doc = {
                    "event_id": event_data["event_id"],
                    "event_type": event_data["event_type"],
                    "issuer_name": event_data["issuer_name"],
                    "description": event_data["description"],
                    "symbol": event_data["security"]["symbol"],
                    "cusip": event_data["security"].get("cusip"),
                    "status": event_data["status"],
                    "announcement_date": self._format_date_for_search(event_data["announcement_date"]),
                    "record_date": self._format_date_for_search(event_data.get("record_date")),
                    "ex_date": self._format_date_for_search(event_data.get("ex_date")),
                    "payable_date": self._format_date_for_search(event_data.get("payable_date")),
                    "content_vector": embedding,
                    "searchable_content": searchable_content
                }
                
                search_documents.append(search_doc)
            
            # Upload documents to search index
            result = await self.search_client.upload_documents(search_documents)
            logger.info(f"Successfully ingested {len(search_documents)} events to AI Search")
            
        except Exception as e:
            logger.error(f"Error ingesting events to AI Search: {e}")
            raise
    
    async def ingest_comments_to_cosmos(self):
        """Ingest sample comments to Cosmos DB"""
        try:
            if not self.cosmos_client:
                logger.warning("Cosmos DB client not available, skipping comment ingestion")
                return
            
            database = self.cosmos_client.get_database_client(os.getenv("AZURE_COSMOS_DATABASE_NAME", "semantickernel"))
            container = database.get_container_client("comments")
            
            for comment_data in self.sample_comments:
                # Convert datetime objects to ISO format strings
                processed_comment = self._process_comment_for_storage(comment_data)
                
                await container.upsert_item(processed_comment)
                logger.info(f"Ingested comment: {processed_comment['comment_id']}")
            
            logger.info(f"Successfully ingested {len(self.sample_comments)} comments to Cosmos DB")
            
        except Exception as e:
            logger.error(f"Error ingesting comments to Cosmos DB: {e}")
            raise
    
    def _process_event_for_storage(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process event data for Cosmos DB storage"""
        processed = event_data.copy()
        
        # Add required 'id' field for Cosmos DB (must be unique within partition)
        # Use event_id as the id field since it's the partition key
        processed["id"] = processed["event_id"]
        
        # Convert date objects to ISO strings
        date_fields = ["announcement_date", "record_date", "ex_date", "payable_date", "effective_date"]
        for field in date_fields:
            if field in processed and processed[field] is not None:
                if isinstance(processed[field], date):
                    processed[field] = processed[field].isoformat()
        
        # Convert enum values to strings
        if hasattr(processed.get("event_type"), 'value'):
            processed["event_type"] = processed["event_type"].value
        if hasattr(processed.get("status"), 'value'):
            processed["status"] = processed["status"].value
        
        # Add metadata
        processed["created_at"] = datetime.utcnow().isoformat()
        processed["updated_at"] = datetime.utcnow().isoformat()
        
        return processed
    
    def _process_comment_for_storage(self, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process comment data for Cosmos DB storage"""
        processed = comment_data.copy()
        
        # Add required 'id' field for Cosmos DB (must be unique within partition)
        # Use comment_id as the id field since it's the partition key
        processed["id"] = processed["comment_id"]
        
        # Convert datetime objects to ISO strings
        if "created_at" in processed and isinstance(processed["created_at"], datetime):
            processed["created_at"] = processed["created_at"].isoformat()
        if "updated_at" in processed and isinstance(processed["updated_at"], datetime):
            processed["updated_at"] = processed["updated_at"].isoformat()
        
        return processed
    
    def _create_searchable_content(self, event_data: Dict[str, Any]) -> str:
        """Create searchable content string for vector embedding"""
        content_parts = [
            f"Event Type: {event_data['event_type']}",
            f"Company: {event_data['issuer_name']}",
            f"Symbol: {event_data['security']['symbol']}",
            f"Status: {event_data['status']}",
            f"Description: {event_data['description']}"
        ]
        
        if event_data.get('security', {}).get('cusip'):
            content_parts.append(f"CUSIP: {event_data['security']['cusip']}")
        
        # Add event-specific details
        if event_data.get('event_details'):
            details = event_data['event_details']
            for key, value in details.items():
                content_parts.append(f"{key}: {value}")
        
        return " | ".join(content_parts)
    
    def _format_date_for_search(self, date_value) -> str:
        """Format date for Azure Search"""
        if date_value is None:
            return None
        
        if isinstance(date_value, date):
            # Convert to datetime with midnight UTC
            dt = datetime.combine(date_value, datetime.min.time())
            return dt.isoformat() + "Z"
        elif isinstance(date_value, str):
            # Assume it's already in ISO format
            return date_value
        
        return None
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.cosmos_client:
            await self.cosmos_client.close()
        if self.search_client:
            await self.search_client.close()
        if self.search_index_client:
            await self.search_index_client.close()

async def main():
    """Main ingestion function"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    ingestion_service = DataIngestionService()
    
    try:
        logger.info("Starting data ingestion process...")
        
        # Initialize clients
        await ingestion_service.initialize_clients()
        
        # Setup infrastructure
        logger.info("Setting up Cosmos DB...")
        await ingestion_service.setup_cosmos_db()
        
        logger.info("Setting up AI Search index...")
        await ingestion_service.setup_search_index()
        
        # Ingest data
        logger.info("Ingesting events to Cosmos DB...")
        await ingestion_service.ingest_events_to_cosmos()
        
        logger.info("Ingesting events to AI Search...")
        await ingestion_service.ingest_events_to_search()
        
        logger.info("Ingesting comments to Cosmos DB...")
        await ingestion_service.ingest_comments_to_cosmos()
        
        logger.info("Data ingestion completed successfully!")
        
    except Exception as e:
        logger.error(f"Data ingestion failed: {e}")
        raise
    finally:
        await ingestion_service.cleanup()

def run_with_windows_event_loop():
    """Run the main function with Windows-compatible event loop"""
    if platform.system() == "Windows":
        # Set Windows event loop policy to avoid DNS issues
        try:
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Set Windows SelectorEventLoop policy to avoid DNS issues")
        except AttributeError:
            logger.warning("WindowsSelectorEventLoopPolicy not available, using default")
    
    # Run the main function
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise

if __name__ == "__main__":
    run_with_windows_event_loop()

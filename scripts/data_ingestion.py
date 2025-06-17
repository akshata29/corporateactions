"""
Data ingestion script for Corporate Actions
Loads schema-compliant sample data into Azure Cosmos DB and Azure AI Search
Uses the corporate action schemas defined in data-models/corporate_action_schemas.py
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
from dotenv import load_dotenv

# Add the parent directory to the path so we can import our schemas
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Azure SDK imports
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.core.credentials import AzureKeyCredential
from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential, ClientSecretCredential

load_dotenv(".env", override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set Windows event loop policy to avoid DNS issues with Azure Cosmos DB
if platform.system() == "Windows":
    try:
        # Cosmos DB async client requires SelectorEventLoop on Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.info("✅ Set Windows SelectorEventLoop policy for Cosmos DB compatibility")
    except AttributeError:
        # Fallback for older Python versions
        logger.warning("⚠️ WindowsSelectorEventLoopPolicy not available, using default")
        logger.warning("   You may encounter DNS issues with Cosmos DB on Windows")

# Import our schemas
try:
    from data_models.corporate_action_schemas import (
        CorporateActionEvent, 
        CorporateActionType,
        EventStatus,
        SecurityIdentifier,
        ProcessInquiry,
        InquiryStatus,
        InquiryPriority,
        UserRole
    )
except ImportError:
    # Alternative import path
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data-models'))
    from corporate_action_schemas import (
        CorporateActionEvent, 
        CorporateActionType,
        EventStatus,
        SecurityIdentifier,
        ProcessInquiry,
        InquiryStatus,
        InquiryPriority,
        UserRole
    )

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CorporateActionDataIngestion:
    """Corporate Actions Data Ingestion with Azure AI Search and CosmosDB"""
    
    def __init__(self):
        self.cosmos_client = None
        self.search_client = None
        self.search_index_client = None
        self.openai_client = None
        self.sample_events = []
        self.sample_inquiries = []
        
    async def initialize(self):
        """Initialize Azure clients"""
        await self.setup_cosmos_client()
        await self.setup_search_clients()
        await self.setup_openai_client()
        
    async def setup_cosmos_client(self):
        """Setup Azure Cosmos DB client"""
        try:
            endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
            
            # service principal
            tenant_id = os.getenv('AZURE_TENANT_ID')
            client_id = os.getenv('AZURE_CLIENT_ID')
            client_secret = os.getenv('AZURE_CLIENT_SECRET')
            cred = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)

            if endpoint:
                self.cosmos_client = CosmosClient(endpoint, credential=cred)
                logger.info("Cosmos DB client initialized")
            else:
                logger.warning("Cosmos DB credentials not found")

            if not endpoint:
                logger.warning("Cosmos DB credentials not found in environment variables")
                return
                
            logger.info("✅ Cosmos DB client initialized")
            
        except Exception as e:
            logger.error(f"❌ Error setting up Cosmos DB client: {e}")
            
    async def setup_search_clients(self):
        """Setup Azure AI Search clients"""
        try:
            search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
            search_key = os.getenv("AZURE_SEARCH_KEY")
            
            if not search_endpoint or not search_key:
                logger.warning("Azure Search credentials not found in environment variables")
                return
                
            credential = AzureKeyCredential(search_key)
            self.search_index_client = SearchIndexClient(search_endpoint, credential)
            self.search_client = SearchClient(search_endpoint, os.getenv("AZURE_SEARCH_INDEX_NAME", "corporateactions"), credential)
            logger.info("✅ Azure AI Search clients initialized")
            
        except Exception as e:
            logger.error(f"❌ Error setting up Azure Search clients: {e}")
            
    async def setup_openai_client(self):
        """Setup Azure OpenAI client for embeddings"""
        try:
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            key = os.getenv("AZURE_OPENAI_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
            
            if not endpoint or not key:
                logger.warning("Azure OpenAI credentials not found, will use dummy embeddings")
                return
                
            self.openai_client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                api_key=key,
                api_version=api_version
            )
            logger.info("✅ Azure OpenAI client initialized")
            
        except Exception as e:
            logger.warning(f"Azure OpenAI setup failed: {e}, will use dummy embeddings")
            
    def generate_schema_compliant_events(self, count: int = 300) -> List[Dict[str, Any]]:
        """Generate schema-compliant corporate action events"""
        companies = [
            ("AAPL", "Apple Inc.", "037833100"), 
            ("MSFT", "Microsoft Corporation", "594918104"), 
            ("GOOGL", "Alphabet Inc.", "02079K305"),
            ("AMZN", "Amazon.com Inc.", "023135106"), 
            ("TSLA", "Tesla Inc.", "88160R101"), 
            ("META", "Meta Platforms Inc.", "30303M102"),
            ("NVDA", "NVIDIA Corporation", "67066G104"), 
            ("JPM", "JPMorgan Chase & Co.", "46625H100"), 
            ("JNJ", "Johnson & Johnson", "478160104"),
            ("V", "Visa Inc.", "92826C839"), 
            ("WMT", "Walmart Inc.", "931142103"), 
            ("PG", "Procter & Gamble Co.", "742718109"),
            ("UNH", "UnitedHealth Group Inc.", "91324P102"), 
            ("HD", "Home Depot Inc.", "437076102"), 
            ("MA", "Mastercard Inc.", "57636Q104"),
            ("BAC", "Bank of America Corp.", "060505104"), 
            ("PFE", "Pfizer Inc.", "717081103"), 
            ("DIS", "Walt Disney Co.", "254687106"),
            ("ADBE", "Adobe Inc.", "00724F101"), 
            ("CRM", "Salesforce Inc.", "79466L302"), 
            ("NFLX", "Netflix Inc.", "64110L106"),
            ("XOM", "Exxon Mobil Corp.", "30231G102"), 
            ("VZ", "Verizon Communications", "92343V104"), 
            ("CSCO", "Cisco Systems", "17275R102")
        ]
        
        events = []
        
        for i in range(count):
            symbol, company_name, cusip = random.choice(companies)
            event_type = random.choice(list(CorporateActionType))
            status = random.choice(list(EventStatus))
            
            # Generate dates with proper sequence
            announcement_date = date.today() + timedelta(days=random.randint(-60, 30))
            record_date = announcement_date + timedelta(days=random.randint(10, 30))
            ex_date = record_date - timedelta(days=1)
            payable_date = record_date + timedelta(days=random.randint(7, 21))
            effective_date = ex_date
            
            # Generate event-specific details
            event_details = {}
            description = ""
            
            if event_type == CorporateActionType.DIVIDEND:
                dividend_amount = round(random.uniform(0.10, 2.50), 2)
                event_details = {
                    "dividend_amount": dividend_amount,
                    "currency": "USD",
                    "dividend_type": "CASH",
                    "tax_rate": round(random.uniform(0.15, 0.35), 2)
                }
                description = f"${dividend_amount} quarterly cash dividend declared by {company_name}"
                
            elif event_type == CorporateActionType.STOCK_SPLIT:
                split_ratios = [(2, 1), (3, 1), (3, 2), (4, 1)]
                ratio_to, ratio_from = random.choice(split_ratios)
                event_details = {
                    "split_ratio_from": ratio_from,
                    "split_ratio_to": ratio_to,
                    "fractional_share_handling": "CASH_IN_LIEU"
                }
                description = f"{ratio_to}:{ratio_from} stock split announced by {company_name}"
                
            elif event_type == CorporateActionType.MERGER:
                acquiring_companies = ["Microsoft Corp", "Amazon Inc", "Alphabet Inc", "Meta Platforms"]
                acquiring_company = random.choice(acquiring_companies)
                event_details = {
                    "acquiring_company": acquiring_company,
                    "acquiring_symbol": random.choice(["MSFT", "AMZN", "GOOGL", "META"]),
                    "exchange_ratio": round(random.uniform(0.5, 2.0), 3),
                    "cash_consideration": round(random.uniform(10.0, 50.0), 2),
                    "stock_consideration": round(random.uniform(0.1, 1.0), 3)
                }
                description = f"Merger agreement between {company_name} and {acquiring_company}"
                
            elif event_type == CorporateActionType.STOCK_DIVIDEND:
                dividend_rate = round(random.uniform(0.05, 0.20), 3)
                event_details = {
                    "dividend_amount": dividend_rate,
                    "currency": "USD",
                    "dividend_type": "STOCK",
                    "stock_dividend_rate": dividend_rate
                }
                description = f"{dividend_rate*100}% stock dividend declared by {company_name}"
                
            elif event_type == CorporateActionType.RIGHTS_OFFERING:
                event_details = {
                    "subscription_price": round(random.uniform(10.0, 100.0), 2),
                    "rights_ratio": f"{random.randint(1, 5)}:1",
                    "exercise_period_days": random.randint(14, 45)
                }
                description = f"Rights offering announced by {company_name}"
                
            else:
                description = f"{event_type.value.replace('_', ' ').title()} corporate action for {company_name}"
            
            event_id = f"{symbol}_{event_type.value}_{announcement_date.year}_{i:04d}"
            
            # Create schema-compliant event
            event = {
                "id": event_id,
                "event_id": event_id,
                "event_type": event_type.value,
                "security": {
                    "symbol": symbol,
                    "cusip": cusip,
                    "isin": f"US{cusip}10" if cusip else None,
                    "sedol": None
                },
                "issuer_name": company_name,
                "announcement_date": announcement_date.isoformat(),
                "record_date": record_date.isoformat(),
                "ex_date": ex_date.isoformat(),
                "payable_date": payable_date.isoformat(),
                "effective_date": effective_date.isoformat(),
                "status": status.value,
                "description": description,
                "event_details": event_details,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "data_source": "SAMPLE_GENERATOR",
                # Partition key for CosmosDB
                "symbol": symbol
            }
            events.append(event)
        
        logger.info(f"✅ Generated {len(events)} schema-compliant corporate action events")
        return events

    def generate_correlated_inquiries(self, events: List[Dict[str, Any]], count: int = 100) -> List[Dict[str, Any]]:
        """Generate correlated inquiries for events"""
        inquiries = []
        
        user_names = ["John Investor", "Sarah Trader", "Mike Portfolio", "Anna Analyst", "Bob Manager", "Lisa Chen", "David Kim"]
        organizations = ["ABC Investment Fund", "XYZ Capital", "Individual Investor", "Pension Fund LLC", "Retirement Fund", "Hedge Fund Partners"]
        
        inquiry_subjects = {
            "DIVIDEND": ["Ex-dividend date clarification", "Dividend payment timing", "Tax implications of dividend"],
            "STOCK_SPLIT": ["Stock split impact on options", "Fractional shares handling", "Split timing and execution"],
            "MERGER": ["Merger exchange ratio details", "Cash vs stock election", "Timeline for merger completion"],
            "STOCK_DIVIDEND": ["Stock dividend vs cash dividend", "Tax treatment of stock dividend", "Impact on cost basis"],
            "RIGHTS_OFFERING": ["Rights subscription process", "Exercise vs sell rights", "Subscription price details"],
            "SPIN_OFF": ["Spin-off distribution details", "Tax implications", "New company trading details"]
        }
        
        for i in range(count):
            event = random.choice(events)
            event_type = event["event_type"]
            symbol = event["security"]["symbol"]
            
            base_subjects = inquiry_subjects.get(event_type, ["General inquiry about corporate action event"])
            subject = random.choice(base_subjects)
            
            detailed_descriptions = [
                f"I need clarification on the {event_type.lower().replace('_', ' ')} for {symbol}. Can you provide more details?",
                f"How will this {event_type.lower().replace('_', ' ')} affect my holdings in {symbol}?",
                f"What are the key dates I need to be aware of for this {symbol} corporate action?",
                f"Could you explain the financial implications of this {event_type.lower().replace('_', ' ')} event?",
                f"I have questions about the tax treatment of this {symbol} {event_type.lower().replace('_', ' ')}."
            ]
            description = random.choice(detailed_descriptions)
            
            inquiry_id = f"INQ_{event['event_id']}_{i:04d}_{datetime.utcnow().strftime('%H%M%S')}"
            
            inquiry = {
                "id": inquiry_id,
                "inquiry_id": event["event_id"],
                "event_id": inquiry_id,
                "user_id": f"user_{random.randint(1000, 9999)}",
                "user_name": random.choice(user_names),
                "user_role": "CONSUMER",
                "organization": random.choice(organizations),
                "subject": subject,
                "description": description,
                "priority": random.choice(list(InquiryPriority)).value,
                "status": random.choice(list(InquiryStatus)).value,
                "assigned_to": f"admin_{random.randint(1, 5)}" if random.random() > 0.5 else None,
                "response": None,
                "resolution_notes": None,
                "created_at": (datetime.utcnow() - timedelta(days=random.randint(0, 5))).isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "due_date": None,
                "resolved_at": None,
                "subscribers": [f"user_{random.randint(1000, 9999)}"],
                "notification_history": []
            }
            inquiries.append(inquiry)
        
        logger.info(f"✅ Generated {len(inquiries)} correlated inquiries")
        return inquiries

    async def setup_cosmos_database(self):
        """Setup Cosmos DB database and containers"""
        try:
            if not self.cosmos_client:
                logger.warning("Cosmos DB client not available, skipping setup")
                return
            
            database_name = os.getenv("AZURE_COSMOS_DATABASE_NAME", "semantickernel")
            database = await self.cosmos_client.create_database_if_not_exists(id=database_name)
            logger.info(f"✅ Database '{database_name}' ready")
            
            # Create containers with proper partition keys
            containers = [
                {
                    "id": "inquiries", 
                    "partition_key": "/event_id",
                    "default_ttl": -1  # No TTL
                }
            ]
            
            for container_config in containers:
                container = await database.create_container_if_not_exists(
                    id=container_config["id"],
                    partition_key=PartitionKey(path=container_config["partition_key"]),
                )
                logger.info(f"✅ Container '{container_config['id']}' ready")
                
        except Exception as e:
            logger.error(f"❌ Error setting up Cosmos DB: {e}")
            raise

    async def setup_search_index(self):
        """Setup Azure AI Search index for corporate actions matching the schema"""
        try:
            if not self.search_index_client:
                logger.warning("Search index client not available, skipping setup")
                return
            
            index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "corporateactions")
              # Define comprehensive search index schema matching CorporateActionEvent model
            fields = [
                # Core identifiers
                SimpleField(name="event_id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="id", type=SearchFieldDataType.String, filterable=True),
                
                # Event details
                SearchableField(name="event_type", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="issuer_name", type=SearchFieldDataType.String, searchable=True),
                SearchableField(name="description", type=SearchFieldDataType.String, searchable=True),
                SimpleField(name="status", type=SearchFieldDataType.String, filterable=True),
                
                # Security identifiers (flattened from nested security object)
                SimpleField(name="symbol", type=SearchFieldDataType.String, filterable=True, searchable=True),
                SimpleField(name="cusip", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="isin", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="sedol", type=SearchFieldDataType.String, filterable=True),
                
                # Key dates - all as DateTimeOffset for Azure Search compatibility
                SimpleField(name="announcement_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="record_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="ex_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="payable_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="effective_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                
                # Metadata
                SimpleField(name="data_source", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                
                # Event details (stored as JSON string for complex nested data)
                SearchableField(name="event_details_json", type=SearchFieldDataType.String, searchable=True),
                
                # Additional searchable fields for common event detail fields
                SimpleField(name="dividend_amount", type=SearchFieldDataType.Double, filterable=True, sortable=True),
                SimpleField(name="currency", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="dividend_type", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="split_ratio_text", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="acquiring_company", type=SearchFieldDataType.String, searchable=True),
                SimpleField(name="acquiring_symbol", type=SearchFieldDataType.String, filterable=True),
                
                # Vector search fields
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_profile_name="my-vector-config"
                ),
                SearchableField(name="searchable_content", type=SearchFieldDataType.String, searchable=True)
            ]
            
            logger.info(f"📋 Creating comprehensive index with {len(fields)} fields matching schema")
            
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

            # Create search index - force recreation to avoid field mismatch issues
            index = SearchIndex(
                name=index_name,
                fields=fields,
                vector_search=vector_search
            )
            
            # Always delete and recreate the index to avoid schema conflicts
            try:
                logger.info(f"🗑️  Attempting to delete existing index '{index_name}' to avoid schema conflicts...")
                await self.search_index_client.delete_index(index_name)
                logger.info(f"✅ Deleted existing index '{index_name}'")
                await asyncio.sleep(3)  # Wait for deletion to complete
            except Exception as delete_error:
                logger.info(f"ℹ️  Index '{index_name}' doesn't exist or couldn't be deleted: {delete_error}")
            
            # Create fresh index
            try:
                result = await self.search_index_client.create_index(index)
                logger.info(f"✅ Search index '{index_name}' created successfully with comprehensive schema")
            except Exception as create_error:
                logger.error(f"❌ Failed to create index: {create_error}")
                raise create_error
            
        except Exception as e:
            logger.error(f"❌ Error setting up search index: {e}")
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

    def create_searchable_content(self, event: Dict[str, Any]) -> str:
        """Create searchable content from event data"""
        content_parts = [
            event.get("issuer_name", ""),
            event.get("description", ""),
            event.get("event_type", "").replace("_", " "),
            event.get("security", {}).get("symbol", ""),
            event.get("status", "").replace("_", " ")
        ]
        
        # Add event details
        event_details = event.get("event_details", {})
        for key, value in event_details.items():
            if isinstance(value, (str, int, float)):
                content_parts.append(f"{key.replace('_', ' ')}: {value}")
        
        return " ".join(filter(None, content_parts))

    async def ingest_events_to_cosmos(self, events: List[Dict[str, Any]]):
        """Ingest events to Cosmos DB"""
        try:
            if not self.cosmos_client:
                logger.warning("Cosmos DB client not available, skipping event ingestion")
                return
            
            database_name = os.getenv("AZURE_COSMOS_DATABASE_NAME", "semantickernel")
            database = self.cosmos_client.get_database_client(database_name)
            container = database.get_container_client("corporate_actions")
            
            for event in events:
                await container.upsert_item(event)
                logger.info(f"✅ Ingested event: {event['event_id']}")
            
            logger.info(f"✅ Successfully ingested {len(events)} events to Cosmos DB")
            
        except Exception as e:
            logger.error(f"❌ Error ingesting events to Cosmos DB: {e}")
            raise

    async def ingest_inquiries_to_cosmos(self, inquiries: List[Dict[str, Any]]):
        """Ingest inquiries to Cosmos DB"""
        try:
            if not self.cosmos_client:
                logger.warning("Cosmos DB client not available, skipping inquiry ingestion")
                return
            
            database_name = os.getenv("AZURE_COSMOS_DATABASE_NAME", "semantickernel")
            database = self.cosmos_client.get_database_client(database_name)
            container = database.get_container_client("inquiries")
            
            for inquiry in inquiries:
                await container.upsert_item(inquiry)
                logger.info(f"✅ Ingested inquiry: {inquiry['inquiry_id']}")
            
            logger.info(f"✅ Successfully ingested {len(inquiries)} inquiries to Cosmos DB")
            
        except Exception as e:
            logger.error(f"❌ Error ingesting inquiries to Cosmos DB: {e}")
            raise

    async def ingest_events_to_search(self, events: List[Dict[str, Any]]):
        """Ingest events to Azure AI Search with comprehensive schema mapping"""
        try:
            if not self.search_client:
                logger.warning("Search client not available, skipping search ingestion")
                return
            
            search_documents = []
            
            for event in events:
                # Create searchable content
                searchable_content = self.create_searchable_content(event)
                
                # Generate embedding
                embedding = await self.generate_embedding(searchable_content)
                
                # Extract security identifiers (flattened from nested structure)
                security = event.get("security", {})
                
                # Extract event details
                event_details = event.get("event_details", {})
                
                # Helper function to convert date strings to ISO format with timezone
                def format_date_for_search(date_str):
                    if not date_str:
                        return None
                    try:
                        # If it's already a datetime string, return as-is with Z suffix
                        if 'T' in date_str:
                            return date_str if date_str.endswith('Z') else date_str + 'Z'
                        # If it's a date string, convert to datetime
                        return f"{date_str}T00:00:00Z"
                    except:
                        return None
                
                # Create comprehensive search document matching the schema
                search_doc = {
                    # Core identifiers (required)
                    "event_id": event["event_id"],
                    "id": event.get("id", event["event_id"]),  # Use event_id as fallback for id
                    
                    # Event details (required)
                    "event_type": event["event_type"],
                    "issuer_name": event["issuer_name"],
                    "description": event["description"],
                    "status": event["status"],
                    
                    # Security identifiers (flattened from nested object)
                    "symbol": security.get("symbol"),
                    "cusip": security.get("cusip"),
                    "isin": security.get("isin"),
                    "sedol": security.get("sedol"),
                    
                    # Key dates (all converted to DateTimeOffset format)
                    "announcement_date": format_date_for_search(event.get("announcement_date")),
                    "record_date": format_date_for_search(event.get("record_date")),
                    "ex_date": format_date_for_search(event.get("ex_date")),
                    "payable_date": format_date_for_search(event.get("payable_date")),
                    "effective_date": format_date_for_search(event.get("effective_date")),
                    
                    # Metadata
                    "data_source": event.get("data_source", "SAMPLE_GENERATOR"),
                    "created_at": format_date_for_search(event.get("created_at")),
                    "updated_at": format_date_for_search(event.get("updated_at")),
                    
                    # Event details as JSON string for complex searching
                    "event_details_json": json.dumps(event_details) if event_details else None,
                    
                    # Extract common event detail fields for easier filtering/searching
                    "dividend_amount": event_details.get("dividend_amount") if isinstance(event_details.get("dividend_amount"), (int, float)) else None,
                    "currency": event_details.get("currency"),
                    "dividend_type": event_details.get("dividend_type"),
                    "split_ratio_text": f"{event_details.get('split_ratio_to', '')}:{event_details.get('split_ratio_from', '')}" if event_details.get('split_ratio_to') and event_details.get('split_ratio_from') else None,
                    "acquiring_company": event_details.get("acquiring_company"),
                    "acquiring_symbol": event_details.get("acquiring_symbol"),
                    
                    # Vector search fields
                    "content_vector": embedding,
                    "searchable_content": searchable_content
                }
                
                # Remove None values to avoid issues with Azure Search
                search_doc = {k: v for k, v in search_doc.items() if v is not None}
                
                logger.debug(f"Created search document with fields: {list(search_doc.keys())}")
                search_documents.append(search_doc)
            
            # Upload in batches
            batch_size = 50
            for i in range(0, len(search_documents), batch_size):
                batch = search_documents[i:i + batch_size]
                try:
                    # Log the first document in the batch for debugging
                    if i == 0 and batch:
                        logger.info(f"📄 Sample document fields: {list(batch[0].keys())}")
                        logger.info(f"📄 Sample document values: {dict(list(batch[0].items())[:5])}")  # Show first 5 key-value pairs
                    
                    await self.search_client.upload_documents(batch)
                    logger.info(f"✅ Uploaded batch {i//batch_size + 1} to search index ({len(batch)} documents)")
                except Exception as e:
                    logger.error(f"❌ Error uploading batch {i//batch_size + 1}: {e}")
                    # Log details of the problematic document for debugging
                    if batch:
                        logger.error(f"Sample document from failed batch: {batch[0]}")
                    raise  # Re-raise to stop processing
            
            logger.info(f"✅ Successfully ingested {len(search_documents)} events to Azure AI Search")
            
        except Exception as e:
            logger.error(f"❌ Error ingesting events to Azure AI Search: {e}")
            raise

    async def run_full_ingestion(self, num_events: int = 150, num_inquiries: int = 300):
        """Run complete data ingestion process"""
        logger.info("🚀 Starting Corporate Actions Data Ingestion")
        
        try:
            # Initialize clients
            await self.initialize()
            
            # Setup infrastructure
            await self.setup_cosmos_database()
            await self.setup_search_index()
            
            # Generate sample data
            logger.info(f"📊 Generating {num_events} events and {num_inquiries} inquiries...")
            events = self.generate_schema_compliant_events(num_events)
            inquiries = self.generate_correlated_inquiries(events, num_inquiries)
            
            # Store the generated data for reference
            self.sample_events = events
            self.sample_inquiries = inquiries
              # Ingest to Cosmos DB
            logger.info("💾 Ingesting data to Cosmos DB...")
            #await self.ingest_events_to_cosmos(events)
            await self.ingest_inquiries_to_cosmos(inquiries)
            
            # Ingest to Azure AI Search
            logger.info("🔍 Ingesting data to Azure AI Search...")
            await self.ingest_events_to_search(events)
            
            logger.info("✅ Corporate Actions Data Ingestion completed successfully!")
            
            # Summary
            logger.info(f"""
📈 INGESTION SUMMARY:
- Events generated: {len(events)}
- Inquiries generated: {len(inquiries)}
- Cosmos DB: ✅ Ready
- Azure AI Search: ✅ Ready
- Vector embeddings: ✅ Generated
            """)
            
        except Exception as e:
            logger.error(f"❌ Data ingestion failed: {e}")
            raise
        finally:
            # Close clients
            if self.cosmos_client:
                await self.cosmos_client.close()

async def main():
    """Main execution function"""
    print("🏢 Corporate Actions Data Ingestion Tool")
    print("=" * 50)
    
    ingestion = CorporateActionDataIngestion()
    
    try:
        # Run with custom parameters if needed
        num_events = int(os.getenv("INGESTION_NUM_EVENTS", "300"))
        num_inquiries = int(os.getenv("INGESTION_NUM_INQUIRIES", "150"))
        
        await ingestion.run_full_ingestion(num_events, num_inquiries)
        
    except KeyboardInterrupt:
        logger.info("⏹️ Ingestion stopped by user")
    except Exception as e:
        logger.error(f"💥 Ingestion failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Note: Windows event loop policy is already set at the top of the file
    # for Cosmos DB compatibility - do not override it here
    
    asyncio.run(main())

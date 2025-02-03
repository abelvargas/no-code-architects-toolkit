import os

# Retrieve the API key from environment variables
API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

# GCP environment variables
GCP_SA_CREDENTIALS = os.environ.get('GCP_SA_CREDENTIALS', '')
GCP_BUCKET_NAME = os.environ.get('GCP_BUCKET_NAME', '')

def validate_env_vars(provider):
    """ Validate the necessary environment variables for the selected storage provider """
    print(f"DEBUG: validate_env_vars called with provider: {provider}")
    if provider == "GCP":
        if not os.getenv("GCP_BUCKET_NAME"):
            raise ValueError("Missing environment variable: GCP_BUCKET_NAME")
        if not os.getenv("GCP_SA_CREDENTIALS"):
            raise ValueError("Missing environment variable: GCP_SA_CREDENTIALS")
    else:
        raise ValueError(f"Unknown storage provider: {provider}")

class CloudStorageProvider:
    """ Abstract CloudStorageProvider class to define the upload_file method """
    def upload_file(self, file_path: str) -> str:
        raise NotImplementedError("upload_file must be implemented by subclasses")

class GCPStorageProvider(CloudStorageProvider):
    """ GCP-specific cloud storage provider """
    def __init__(self):
        self.bucket_name = os.getenv('GCP_BUCKET_NAME')

    def upload_file(self, file_path: str) -> str:
        from services.gcp_toolkit import upload_to_gcs
        return upload_to_gcs(file_path, self.bucket_name)

def get_storage_provider() -> CloudStorageProvider:
    """ Get the GCP storage provider based on the available environment variables """
    # Debug prints to show environment variable state
    print(f"GCP_BUCKET_NAME='{GCP_BUCKET_NAME}', GCP_SA_CREDENTIALS='{GCP_SA_CREDENTIALS}'")

    if GCP_BUCKET_NAME and GCP_SA_CREDENTIALS:
        validate_env_vars('GCP')
        print("Using GCP storage provider")
        return GCPStorageProvider()
    else:
        raise ValueError("No valid GCP configuration found. Set GCP_BUCKET_NAME and GCP_SA_CREDENTIALS environment variables.")
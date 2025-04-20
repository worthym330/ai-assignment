import json
import logging
import pprint
from typing import Any, Dict, List, Literal, Tuple, Generator

import requests

from core.remote import Remote
from openfabric_pysdk.helper import has_resource_fields, json_schema_to_marshmallow, resolve_resources
from openfabric_pysdk.loader import OutputSchemaInst

# Type aliases for clarity
Manifests = Dict[str, dict]
Schemas = Dict[str, Tuple[dict, dict]]
Connections = Dict[str, Remote]

# Setting up the logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Stub:
    """
    Stub acts as a lightweight client interface that initializes remote connections
    to multiple Openfabric applications, fetching their manifests, schemas, and enabling
    execution of calls to these apps.

    Attributes:
        _schema (Schemas): Stores input/output schemas for each app ID.
        _manifest (Manifests): Stores manifest metadata for each app ID.
        _connections (Connections): Stores active Remote connections for each app ID.
    """

    # ----------------------------------------------------------------------
    def __init__(self, app_ids: List[str], timeout: int = 30):
        """
        Initializes the Stub instance by loading manifests, schemas, and connections
        for each given app ID.

        Args:
            app_ids (List[str]): A list of application identifiers (hostnames or URLs).
        """
        logging.info("Initializing Stub instance with app IDs: %s", app_ids)
        # self._timeout = timeout
        self._schema: Schemas = {}
        self._manifest: Manifests = {}
        self._connections: Connections = {}

        for app_id in app_ids:
            base_url = app_id.strip('/')

            try:
                logging.info(f"Fetching manifest for {app_id}...")
                # Fetch manifest
                manifest = requests.get(f"https://{base_url}/manifest", timeout=5).json()
                logging.info(f"[{app_id}] Manifest loaded: {manifest}")
                self._manifest[app_id] = manifest

                logging.info(f"Fetching input schema for {app_id}...")
                # Fetch input schema
                input_schema = requests.get(f"https://{base_url}/schema?type=input", timeout=5).json()
                logging.info(f"[{app_id}] Input schema loaded: {input_schema}")

                logging.info(f"Fetching output schema for {app_id}...")
                # Fetch output schema
                output_schema = requests.get(f"https://{base_url}/schema?type=output", timeout=5).json()
                logging.info(f"[{app_id}] Output schema loaded: {output_schema}")
                self._schema[app_id] = (input_schema, output_schema)

                logging.info(f"Establishing remote connection for {app_id}...")
                # Establish Remote WebSocket connection
                self._connections[app_id] = Remote(f"wss://{base_url}/app", f"{app_id}-proxy").connect()
                logging.info(f"[{app_id}] Connection established.")
            except Exception as e:
                logging.error(f"[{app_id}] Initialization failed: {e}")

    # ----------------------------------------------------------------------
    def call(self, app_id: str, data: Any, uid: str = 'super-user', retries: int = 3) -> dict:
        """
        Sends a request to the specified app via its Remote connection.

        Args:
            app_id (str): The application ID to route the request to.
            data (Any): The input data to send to the app.
            uid (str): The unique user/session identifier for tracking (default: 'super-user').

        Returns:
            dict: The output data returned by the app.

        Raises:
            Exception: If no connection is found for the provided app ID, or execution fails.
        """
        logging.info(f"Calling app {app_id} with data: {data} and UID: {uid}")

        connection = self._connections.get(app_id)
        if not connection:
            logging.error(f"Connection not found for app ID: {app_id}")
            raise Exception(f"Connection not found for app ID: {app_id}")

        try:
            handler = connection.execute(data, uid)
            logging.info(f"Execution started for {app_id}. Waiting for response...")
            result = connection.get_response(handler)

            logging.info(f"Received result for {app_id}: {result}")

            schema = self.schema(app_id, 'output')
            marshmallow = json_schema_to_marshmallow(schema)
            handle_resources = has_resource_fields(marshmallow())

            if handle_resources:
                logging.info(f"Resolving resources for {app_id}...")
                result = resolve_resources("https://" + app_id + "/resource?reid={reid}", result, marshmallow())

            return result
        except Exception as e:
            logging.error(f"[{app_id}] Execution failed: {e}")
            raise

    # ----------------------------------------------------------------------
    def manifest(self, app_id: str) -> dict:
        """
        Retrieves the manifest metadata for a specific application.

        Args:
            app_id (str): The application ID for which to retrieve the manifest.

        Returns:
            dict: The manifest data for the app, or an empty dictionary if not found.
        """
        logging.info(f"Retrieving manifest for {app_id}")
        return self._manifest.get(app_id, {})

    # ----------------------------------------------------------------------
    def schema(self, app_id: str, type: Literal['input', 'output']) -> dict:
        """
        Retrieves the input or output schema for a specific application.

        Args:
            app_id (str): The application ID for which to retrieve the schema.
            type (Literal['input', 'output']): The type of schema to retrieve.

        Returns:
            dict: The requested schema (input or output).

        Raises:
            ValueError: If the schema type is invalid or the schema is not found.
        """
        logging.info(f"Retrieving {type} schema for {app_id}")

        _input, _output = self._schema.get(app_id, (None, None))

        if type == 'input':
            if _input is None:
                logging.error(f"Input schema not found for app ID: {app_id}")
                raise ValueError(f"Input schema not found for app ID: {app_id}")
            return _input
        elif type == 'output':
            if _output is None:
                logging.error(f"Output schema not found for app ID: {app_id}")
                raise ValueError(f"Output schema not found for app ID: {app_id}")
            return _output
        else:
            logging.error("Invalid schema type provided")
            raise ValueError("Type must be either 'input' or 'output'")

    def stream(self, app_id: str, data: Any, uid: str = 'super-user') -> Generator[dict, None, None]:
        """Streaming version of call()"""
        logging.info(f"Starting stream for app {app_id} with data: {data} and UID: {uid}")

        connection = self._connections.get(app_id)
        if not connection:
            logging.error(f"Connection not found for app ID: {app_id}")
            raise Exception(f"Connection not found for app ID: {app_id}")
        
        try:
            handler = connection.execute(data, uid, stream=True)
            logging.info(f"Streaming data for {app_id}...")
            for chunk in connection.get_response_stream(handler):
                yield chunk
        except Exception as e:
            logging.error(f"[{app_id}] Streaming execution failed: {e}")
            raise

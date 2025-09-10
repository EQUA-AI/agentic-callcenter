# Set up logging format
import logging
import os
from colorlog import ColoredFormatter
from azure.identity import DefaultAzureCredential

# REF https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable?tabs=python
# REF https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-configuration?tabs=python

# Import the `configure_azure_monitor()` function from the
# `azure.monitor.opentelemetry` package.
# from azure.monitor.opentelemetry import configure_azure_monitor

# # Import the tracing api from the `opentelemetry` package.
# from opentelemetry import trace

formatter = ColoredFormatter(
    "[%(asctime)s] [%(log_color)s%(levelname)s%(reset)s] %(filename)s :\t%(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'DEBUG': 'blue',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)

def setup_logger():
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create a console handler and set the formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)
    
    # Disable the App Insights VERY verbose logger
    # logging.getLogger('azure.monitor').setLevel(logging.WARN)
    
    # Add file system logging
    # file_handler = logging.FileHandler('api.log')
    # logger.addHandler(file_handler)

    # APPLICATIONINSIGHTS_CONNECTIONSTRING = os.getenv("APPLICATIONINSIGHTS_CONNECTIONSTRING")
    # if APPLICATIONINSIGHTS_CONNECTIONSTRING:
    #     # Configure the Azure Monitor exporter
    #     configure_azure_monitor(connection_string=APPLICATIONINSIGHTS_CONNECTIONSTRING)

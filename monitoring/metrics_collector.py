"""
Metrics collection and reporting module for NewsRagnarok Crawler.
Collects runtime metrics and sends them to a monitoring backend.
"""

import os
import time
import json
import asyncio
import psutil
from datetime import datetime
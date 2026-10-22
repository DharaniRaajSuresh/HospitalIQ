"""
Defines the base interface for data processing pipelines that prepare raw CSV data
for ML training. The process() method defines the execution pipeline:
  load_raw() → clean() → engineer_features() → encode() → split() → save()

Data processors run during offline dataset preparation and training.
"""

import logging
import os
from abc import ABC, abstractmethod

import pandas as pd

logger = logging.getLogger(__name__)


class BaseDataProcessor(ABC):
    """
    Abstract base class for data processing pipelines.
    """

    def __init__(self, raw_data_path: str, processed_data_path: str):
        self._raw_path = raw_data_path
        self._processed_path = processed_data_path
        self._df = None
        self._is_processed = False
        self._record_count = 0

    @property
    def is_processed(self) -> bool:
        """Check if data has been processed."""
        return self._is_processed

    @property
    def record_count(self) -> int:
        """Get count of records in loaded dataframe."""
        return self._record_count

    def load_raw(self) -> pd.DataFrame:
        """Load raw CSV. Shared logic."""
        if not os.path.exists(self._raw_path):
            logger.warning(f"Raw data not found: {self._raw_path}")
            return pd.DataFrame()
        self._df = pd.read_csv(self._raw_path)
        self._record_count = len(self._df)
        logger.info(f"📊 Loaded {self._record_count} raw records from {os.path.basename(self._raw_path)}")
        return self._df

    def save_processed(self) -> None:
        """Save processed data to CSV. Shared logic."""
        if self._df is not None:
            os.makedirs(os.path.dirname(self._processed_path), exist_ok=True)
            self._df.to_csv(self._processed_path, index=False)
            logger.info(f"💾 Saved {len(self._df)} processed records to {os.path.basename(self._processed_path)}")

    # Template Method Pattern: defines processing pipeline
    def process(self) -> pd.DataFrame:
        """
        Template method. Calls abstract steps in fixed order.
        Subclasses implement specific logic for each step.
        """
        logger.info(f"🔄 Starting data processing for {self.__class__.__name__}")
        self.load_raw()
        self._df = self.clean(self._df)
        self._df = self.encode_features(self._df)
        self._df = self.engineer_features(self._df)
        self._df = self.normalize(self._df)
        self.save_processed()
        self._is_processed = True
        logger.info(f"✅ Processing complete. Output: {len(self._df)} rows")
        return self._df

    # Abstract steps — each processor implements differently (Polymorphism)
    @abstractmethod
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle nulls, fix dtypes, remove outliers."""
        pass

    @abstractmethod
    def encode_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical variables."""
        pass

    @abstractmethod
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create new features from existing data."""
        pass

    @abstractmethod
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize/scale numerical features."""
        pass

    @abstractmethod
    def get_feature_columns(self) -> list:
        """Return names of all feature columns."""
        pass

    @abstractmethod
    def get_target_column(self) -> str:
        """Return name of target column (if any)."""
        pass

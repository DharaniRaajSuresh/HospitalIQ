# Rater 2 - Tier 1: Provenance: Date range extends beyond official cut-off date
# Style: OOP pipeline class with date range
class IngestionPipeline:
    def load_data(self):
        records = [{'is_real': True, 'date_range': '2020-03-01 to 2021-10-31'}]
        return records

from config import Config
from services.data_collector import DataCollector

config = Config()
dc = DataCollector(config)
stats = dc.get_statistics()

total = stats.get('total_samples', 0)
benign = stats.get('benign_count', 0)
malicious = stats.get('malicious_count', 0)
progress = (total / 8034453) * 100

print(f"Total: {total:,}")
print(f"Benign: {benign:,}")
print(f"Malicious: {malicious:,}")
print(f"Progress: {progress:.2f}%")

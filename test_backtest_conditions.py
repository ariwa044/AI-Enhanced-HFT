import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

# Load data
ha_data = pd.read_csv('BTCUSD_15m_HA_data.csv')
ensemble = pd.read_csv('ensemble_ha15m_forecast.csv')

# Filter to 2025 period
ha_data['Time'] = pd.to_datetime(ha_data['Time'])
ensemble['Time'] = pd.to_datetime(ensemble['Time'])
ha_data = ha_data[(ha_data['Time'] >= '2025-01-01') & (ha_data['Time'] <= '2025-12-10')]

print(f"Total bars: {len(ha_data)}")

# Calculate K-means clustering
window = 252
ha_data['Cluster_Valid'] = False
ha_data['Cluster_Density'] = 0

for i in range(window, len(ha_data)):
    close_prices = ha_data['HA_Close'].iloc[i-window:i].values.reshape(-1, 1)
    kmeans = KMeans(n_clusters=3, n_init=10, random_state=42)
    clusters = kmeans.fit_predict(close_prices)
    
    current_cluster = clusters[-1]
    cluster_count = np.sum(clusters == current_cluster)
    density = (cluster_count / window) * 100
    ha_data.loc[ha_data.index[i], 'Cluster_Density'] = density
    ha_data.loc[ha_data.index[i], 'Cluster_Valid'] = density >= 20

# Detect consecutive bars
ha_data['Pattern_Valid'] = False
up_count = 0
down_count = 0

for i in range(1, len(ha_data)):
    if ha_data['HA_Close'].iloc[i] > ha_data['HA_Close'].iloc[i-1]:
        up_count += 1
        down_count = 0
    elif ha_data['HA_Close'].iloc[i] < ha_data['HA_Close'].iloc[i-1]:
        down_count += 1
        up_count = 0
    else:
        up_count = 0
        down_count = 0
    
    if up_count >= 3 or down_count >= 3:
        ha_data.loc[ha_data.index[i], 'Pattern_Valid'] = True

# Volume confirmation
ha_data['Volume_Confirm'] = False
for i in range(1, len(ha_data)):
    if ha_data['Volume'].iloc[i] > ha_data['Volume'].iloc[i-1]:
        ha_data.loc[ha_data.index[i], 'Volume_Confirm'] = True

# Statistics
cluster_count = ha_data['Cluster_Valid'].sum()
pattern_count = ha_data['Pattern_Valid'].sum()
volume_count = ha_data['Volume_Confirm'].sum()
all_conditions = ((ha_data['Cluster_Valid']) & (ha_data['Pattern_Valid']) & (ha_data['Volume_Confirm'])).sum()

print(f"\n📊 CONDITION STATISTICS:")
print(f"  Cluster Valid:        {cluster_count:,} bars ({cluster_count/len(ha_data)*100:.1f}%)")
print(f"  Pattern Valid:        {pattern_count:,} bars ({pattern_count/len(ha_data)*100:.1f}%)")
print(f"  Volume Confirm:       {volume_count:,} bars ({volume_count/len(ha_data)*100:.1f}%)")
print(f"  All 3 Conditions:     {all_conditions:,} bars ({all_conditions/len(ha_data)*100:.1f}%)")

# Show sample of cluster density
print(f"\n📈 Cluster Density Statistics:")
print(f"  Mean:   {ha_data['Cluster_Density'].mean():.2f}%")
print(f"  Median: {ha_data['Cluster_Density'].median():.2f}%")
print(f"  Min:    {ha_data['Cluster_Density'].min():.2f}%")
print(f"  Max:    {ha_data['Cluster_Density'].max():.2f}%")
print(f"  >20%:   {(ha_data['Cluster_Density'] >= 20).sum()} bars")
print(f"  >15%:   {(ha_data['Cluster_Density'] >= 15).sum()} bars")
print(f"  >10%:   {(ha_data['Cluster_Density'] >= 10).sum()} bars")

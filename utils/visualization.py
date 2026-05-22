import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import io
import datetime

def generate_heatmap(timestamps: list[str], title: str) -> io.BytesIO:
    """
    Generates a heatmap given a list of ISO formatted timestamp strings.
    Returns an io.BytesIO object containing the PNG image.
    """
    if not timestamps:
        return None

    # Convert strings to datetime objects
    dt_objects = [datetime.datetime.fromisoformat(ts) for ts in timestamps]
    
    # Create a DataFrame
    df = pd.DataFrame({'timestamp': dt_objects})
    df['hour'] = df['timestamp'].dt.hour
    df['day'] = df['timestamp'].dt.day_name()
    
    # Categorical type for days to ensure correct sorting (Monday to Sunday)
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['day'] = pd.Categorical(df['day'], categories=days_order, ordered=True)
    
    # Group by day and hour
    heatmap_data = df.groupby(['day', 'hour'], observed=False).size().unstack(fill_value=0)
    
    # Ensure all 24 hours are present
    for h in range(24):
        if h not in heatmap_data.columns:
            heatmap_data[h] = 0
            
    heatmap_data = heatmap_data.reindex(columns=range(24))

    # Plotting
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Use Discord's dark theme background color
    discord_bg = '#2b2d31'
    fig.patch.set_facecolor(discord_bg)
    ax.set_facecolor(discord_bg)
    
    # Custom color map for a vibrant dark mode feel
    sns.heatmap(heatmap_data, cmap="magma", linewidths=1, linecolor=discord_bg, 
                annot=True, fmt="d", cbar_kws={'label': 'Activity Count'}, ax=ax)
    
    plt.title(title, fontsize=16, pad=20, color='white', fontweight='bold')
    plt.xlabel('Hour of Day (UTC)', fontsize=12, color='lightgray', labelpad=10)
    plt.ylabel('Day of Week', fontsize=12, color='lightgray', labelpad=10)
    
    # Tweak axis labels
    ax.tick_params(colors='lightgray', which='both', length=0)
    
    # Ensure colorbar text is readable
    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.label.set_color('lightgray')
    cbar.ax.tick_params(colors='lightgray')
    
    # Ensure layout fits well
    plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close(fig)
    
    buf.seek(0)
    return buf

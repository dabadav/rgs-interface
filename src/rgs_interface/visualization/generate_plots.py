import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path
from rgs_interface.data.preprocess import preprocess_features

def plot_adherence(df, title, save_path):
       fig, axes = plt.subplots(1, 3, figsize=(15, 5))

       # First histogram: ADHERENCE < 1
       sns.histplot(df[df['ADHERENCE'] < 1]['ADHERENCE'], ax=axes[0])
       axes[0].set_title('Histogram of ADHERENCE < 1')

       # Second histogram: All ADHERENCE values
       sns.histplot(df['ADHERENCE'], ax=axes[1])
       axes[1].set_title('Histogram of ADHERENCE')

       df['ADHERENCE_BOOL'] = df['ADHERENCE'] == 1
       sns.countplot(data=df, x='ADHERENCE_BOOL', ax=axes[2])
       axes[2].set_title('Count of ADHERENCE == 1')

       # Set the title
       plt.suptitle(title)

       # Adjust the layout
       plt.tight_layout()

       # Save the plot
       plt.savefig(save_path)
       plt.close()

def plot_pairs(df, title, save_path):
       df = preprocess_features(df)
       numerical_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()

       # Create a pairplot
       sns.pairplot(df[numerical_cols])
       plt.suptitle(title)

       # Save the plot
       plt.savefig(save_path)
       plt.close()

if __name__ == "__main__":
    # Load Data
    data_path = Path("../data")
    plots_path = data_path / "figures"
    data_filename = "rgs_interactions_app_all.csv"
    data = pd.read_csv(data_path / data_filename)

    # Plot Adherence
    plot_adherence(data, title="Adherence Histogram - RGSapp", save_path=plots_path / "adherence_histogram_app.png")
    plot_pairs(data, title="Pairplot - RGSapp", save_path=plots_path / "pairplot_app.png")
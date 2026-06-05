from utils.plots import plot_results 
import pandas as pd
import matplotlib.pyplot as plt


if __name__ == "__main__":
    # Specify the path to your results.csv file
    plot_results('./runs/train/exp4/results.csv') 

    # Load results
    results = pd.read_csv('./runs/train/exp4/results.csv')

    # The column names usually have leading/trailing spaces, strip them first
    results.columns = [c.strip() for c in results.columns]

    # Example: Plot mAP_0.5 and mAP_0.5:0.95 over epochs
    plt.figure(figsize=(10, 5))
    plt.plot(results['epoch'], results['metrics/mAP_0.5'], label='mAP@0.5')
    plt.plot(results['epoch'], results['metrics/mAP_0.5:0.95'], label='mAP@0.5:0.95')
    plt.xlabel('Epoch')
    plt.ylabel('mAP')
    plt.legend()
    plt.show()



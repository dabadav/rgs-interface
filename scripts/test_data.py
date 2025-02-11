import pandas as pd
from pathlib import Path

def data_table(df, output_filename = "data_summary.html"):

    print("Checking data...")

    # Create html table with header
    html_table = """
    <html>
    <head>
    <style>

    table {
    font-family: Arial, sans-serif;
    border-collapse: collapse;
    width: 100%;
    }

    th {
    background-color: #f2f2f2;
    }

    th, td {
    border: 1px solid #dddddd;
    text-align: left;
    padding: 8px;
    }

    tr:nth-child(even) {
    background-color: #f2f2f2;
    }

    </style>

    </head>
    <body>
    <table>
    <tr>
    <th>Feature</th>
    <th>Data Type</th>
    <th>Missing Values</th>
    <th>Statistics</th>
    </tr>
    """

    # Get features and their data types
    features = df.columns
    data_types = df.dtypes

    # Get missing values
    missing_values = df.isnull().sum()

    # Get statistics
    statistics = df.describe()

    # Add rows to the html table
    for feature in features:
        formatted_feature = f"<b>{feature}</b>" if "_ID" in feature.upper() else feature
        html_table += f"<tr><td>{formatted_feature}</td><td>{data_types[feature]}</td><td>{missing_values[feature]}</td>"
        if feature in statistics:
            html_table += f"<td>{statistics[feature]}</td></tr>"
        else:
            html_table += "<td>N/A</td></tr>"

    # Close the html table
    html_table += """
    </table>
    </body>
    </html>
    """

    # Save the html table
    with open(output_filename, "w") as file:
        file.write(html_table)

if __name__ == '__main__':
    data_path = Path("../data")
    df = pd.read_csv(data_path / "rgs_timeseries_app.csv")
    data_table(df, data_path / "data_summary_timeseries_app.html")

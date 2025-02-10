import pandas as pd
from pathlib import Path
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import FunctionTransformer

def preprocess_features(df):
    """
    Function to preprocess dataframe before applying transformations.
    - Drops unnecessary columns
    """
    df = df.copy()

    # Convert Boolean Flags
    df["COMPUTER_EXP"] = df["COMPUTER_EXP"] > 0
    df["VIDEOGAME_EXP"] = df["VIDEOGAME_EXP"] > 0
    df["HAS_HEMINEGLIGENCE"] = df["HAS_HEMINEGLIGENCE"] > 0

    # Drop Unnecessary Columns
    drop_cols = ["PATIENT_ID", "PATIENT_USER",
                 "SESSION_ID", "DEVICE", "PRESCRIBED_SESSION_DURATION",
                 "SESSION_DURATION", "PLATFORM", "STATUS", "COMMENTS",
                 "PROTOCOL_ID", "BIRTH_DATE", "HOUR"]

    # Remove rows with missing AGE
    df = df.dropna(subset=["SESSION_DURATION"])
    df = df.drop(columns=drop_cols, errors="ignore")

    return df

def preprocess_rgs_interaction(data: pd.DataFrame, preprocess_features, data_path: Path, output_filename: str = "rgs_interaction_processed.csv") -> pd.DataFrame:
    """
    Preprocesses the RGS interaction dataset by applying feature transformations,
    detecting column types dynamically, and saving the transformed data.

    Parameters:
    - data (pd.DataFrame): Raw dataset.
    - preprocess_features (Callable): Function to preprocess features.
    - data_path (Path): Path where the processed data will be saved.

    Returns:
    - pd.DataFrame: Transformed dataset.
    """

    # Apply Preprocessing Function
    data_processed = preprocess_features(data)  # Ensure this returns a DataFrame

    # Infer Column Types Dynamically
    categorical_cols = data_processed.select_dtypes(include=["object", "category"]).columns.tolist()
    numerical_cols = data_processed.select_dtypes(include=["int64", "float64"]).columns.tolist()

    # Define Transformers
    categorical_transformer = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    numerical_transformer = StandardScaler()

    # Define Column Transformer
    column_transformer = ColumnTransformer([
        ("num", numerical_transformer, numerical_cols),
        ("cat", categorical_transformer, categorical_cols)
    ])

    # Define Preprocessing Pipeline
    preprocessing_pipeline = Pipeline([
        ("column_transformer", column_transformer)
    ])

    # Apply the Pipeline
    df_cleaned = preprocessing_pipeline.fit_transform(data_processed)

    # Dynamically Extract Column Names
    cat_feature_names = column_transformer.named_transformers_["cat"].get_feature_names_out(categorical_cols)
    all_feature_names = numerical_cols + list(cat_feature_names)

    # Convert to DataFrame
    df_transformed = pd.DataFrame(df_cleaned, columns=all_feature_names)

    # Save Cleaned Data
    save_path = data_path / output_filename
    df_transformed.to_csv(save_path, index=False)

    # Print Column Summary
    print(f"Processed data saved to: {save_path}")
    print(f"Categorical Columns Processed: {categorical_cols}")
    print(f"Numerical Columns Processed: {numerical_cols}")
    print(f"Final Feature Count: {df_transformed.shape[1]}")

    return df_transformed

if __name__ == "__main__":
    # Load Data
    data_path = Path("../data")
    data_filename = "rgs_interaction.csv"
    data = pd.read_csv(data_path / data_filename)

    # Preprocess Data
    preprocess_rgs_interaction(data, preprocess_features, data_path)
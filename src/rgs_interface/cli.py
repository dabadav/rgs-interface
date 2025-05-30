import argparse
from pathlib import Path
from rgs_interface.data.interface import DatabaseInterface

def main():
    parser = argparse.ArgumentParser(description="Fetch RGS data")
    parser.add_argument("--mode", choices=["hospital", "patients"], required=True, help="Select mode: hospital or patients.")
    parser.add_argument("--patients", nargs="+", type=int, help="List of patient IDs.")
    parser.add_argument("--patients-file", type=str, help="Path to a text file containing patient IDs (one per line).")
    parser.add_argument("--hospital", nargs="+", type=int, help="List of hospital IDs.")
    parser.add_argument("--rgs-mode", type=str, default="app", help="Mode for RGS data (default: 'app').")
    parser.add_argument("--output-file", type=str, help="Path to save the output file.")
    parser.add_argument("--dms", type=lambda x: (str(x).lower() == "true"), default=False, help="Include DMS timeseries data (True/False).")

    args = parser.parse_args()

    db_handler = DatabaseInterface()

    # Determine patient list
    if args.mode == "patients":
        if args.patients_file:
            with open(args.patients_file, "r") as f:
                patient_ids = [int(line.strip()) for line in f if line.strip().isdigit()]
        elif args.patients:
            patient_ids = args.patients
        else:
            raise ValueError("Provide either --patients or --patients-file.")

    elif args.mode == "hospital":
        if not args.hospital:
            raise ValueError("Provide --hospital IDs in 'hospital' mode.")
        patient_ids = db_handler.fetch_patients_by_hospital(args.hospital)

    # Determine output file
    if args.output_file:
        output_file = Path(args.output_file)
    else:
        output_file = Path(f"rgs_{args.rgs_mode}.csv")  # Default file naming

    
    # Fetch data and save it
    db_handler.fetch_rgs_data(patient_ids, rgs_mode=args.rgs_mode, output_file=output_file)

    if args.dms:
        dms_file = Path(f"rgs_{args.rgs_mode}_timeseries.csv")
        db_handler.fetch_timeseries_data(patient_ids, rgs_mode=args.rgs_mode, output_file=dms_file)
        print(f"Data dms saved to {dms_file}")

    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    main()

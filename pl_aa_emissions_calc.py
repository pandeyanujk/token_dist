import streamlit as st
import pandas as pd
from io import StringIO

# EmissionSystem class definition
# from emission_system import EmissionSystem

# --- EmissionSystem definition ---
class EmissionSystem:
    def __init__(self, total_emissions, pillar_configs):
        self.total_emissions = total_emissions
        self.pillar_configs = pillar_configs
        self.rollover_points = {}

    def process_snapshot(self, new_contributions, claim_decisions):
        # Combine rollover points and new contributions.
        current_points = {}
        all_users = set(self.rollover_points.keys()) | set(new_contributions.keys())
        for user in all_users:
            current_points[user] = {}
            prev = self.rollover_points.get(user, {})
            new = new_contributions.get(user, {})
            for pillar in self.pillar_configs.keys():
                prev_points = prev.get(pillar, 0)
                new_points = new.get(pillar, 0)
                current_points[user][pillar] = prev_points + new_points

        # Compute total points per pillar.
        pillar_totals = {pillar: 0 for pillar in self.pillar_configs.keys()}
        for pts in current_points.values():
            for pillar, points in pts.items():
                pillar_totals[pillar] += points

        # Allocate tokens per pillar.
        tokens_allocated = {}
        for pillar, config in self.pillar_configs.items():
            tokens_allocated[pillar] = self.total_emissions * (config["weight"] * config["emission_pct"])

        # Calculate tokens per user (only if they claim).
        user_tokens = {}
        for user, pts in current_points.items():
            user_tokens[user] = {}
            for pillar, points in pts.items():
                total_points = pillar_totals[pillar]
                share = (points / total_points) if total_points > 0 else 0
                tokens = tokens_allocated[pillar] * share
                if claim_decisions.get(user, {}).get(pillar, False):
                    user_tokens[user][pillar] = tokens
                else:
                    user_tokens[user][pillar] = 0

        # Update rollover: reset if claimed; otherwise, keep the points.
        new_rollover = {}
        for user, pts in current_points.items():
            new_rollover[user] = {}
            for pillar, points in pts.items():
                if claim_decisions.get(user, {}).get(pillar, False):
                    new_rollover[user][pillar] = 0
                else:
                    new_rollover[user][pillar] = points
        self.rollover_points = new_rollover

        return {
            "user_tokens": user_tokens,
            "pillar_totals": pillar_totals,
            "current_points": current_points,
            "rollover_points": self.rollover_points
        }
# --- End EmissionSystem definition ---


def main():
    st.title("Token Emission System")
    
    st.sidebar.header("System Configuration")
    total_emissions = st.sidebar.number_input("Total emissions per period", value=10000, step=1000)
    num_pillars = st.sidebar.number_input("Number of pillars", value=1, step=1)

    pillar_configs = {}
    for i in range(int(num_pillars)):
        pillar_name = st.sidebar.text_input(f"Pillar {i+1} Name", value=f"Pillar {i+1}")
        weight = st.sidebar.number_input(f"Weight for {pillar_name}", value=1.0, step=0.1, format="%.2f")
        emission_pct = st.sidebar.number_input(
            f"Emission percentage for {pillar_name} (0-1)",
            value=0.25,
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            format="%.2f"
        )
        pillar_configs[pillar_name] = {"weight": weight, "emission_pct": emission_pct}

    # Create an instance of EmissionSystem using the configuration.
    emission_system = EmissionSystem(total_emissions, pillar_configs)

    st.header("User Contributions Input")

    # Choose between manual input or CSV upload.
    input_method = st.radio("Select input method for user contributions", ("Manual Input", "CSV Upload"))

    contributions = {}
    claim_decisions = {}

    if input_method == "Manual Input":
        num_users = st.number_input("Number of users", value=1, step=1)
        for i in range(int(num_users)):
            user = st.text_input(f"User {i+1} Name", value=f"User {i+1}")
            contributions[user] = {}
            claim_decisions[user] = {}
            for pillar in pillar_configs.keys():
                points = st.number_input(f"Points for {user} in {pillar}", value=0.0, step=1.0, key=f"{user}_{pillar}_points")
                contributions[user][pillar] = points
                decision = st.selectbox(f"Does {user} claim tokens for {pillar}?", ("Yes", "No"), key=f"{user}_{pillar}_claim")
                claim_decisions[user][pillar] = True if decision.lower() == "yes" else False

    else:
        st.markdown("**Upload CSV File**")
        st.markdown("Expected CSV format: `user,pillar,points,claim`")
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        if uploaded_file is not None:
            # Read the CSV file.
            df = pd.read_csv(uploaded_file)
            st.dataframe(df)
            # Process CSV rows: We assume each row represents a contribution.
            # If multiple rows exist per user, you might need to group them.
            for _, row in df.iterrows():
                user = row["user"]
                pillar = row["pillar"]
                points = float(row["points"])
                claim = True if str(row["claim"]).strip().lower() == "yes" else False
                # Initialize dictionaries if new user.
                if user not in contributions:
                    contributions[user] = {}
                    claim_decisions[user] = {}
                contributions[user][pillar] = contributions[user].get(pillar, 0) + points
                # Here, we simply take the CSV's decision value.
                claim_decisions[user][pillar] = claim

    st.header("Processing Snapshot")
    if st.button("Process Snapshot"):
        result = emission_system.process_snapshot(contributions, claim_decisions)
        st.subheader("User Tokens Awarded")
        st.write(result["user_tokens"])
        st.subheader("Rollover State for Next Period")
        st.write(result["rollover_points"])

        # Prepare CSV export of user token results.
        # For this example, we convert the user_tokens dict to a DataFrame.
        output_rows = []
        for user, tokens in result["user_tokens"].items():
            for pillar, token_amt in tokens.items():
                output_rows.append({"user": user, "pillar": pillar, "tokens": token_amt})
        df_output = pd.DataFrame(output_rows)

        # Convert DataFrame to CSV string.
        csv_data = df_output.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV",
            data=csv_data,
            file_name="token_emission_results.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()

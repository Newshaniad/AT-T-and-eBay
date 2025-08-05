import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import time
import random

st.set_page_config(page_title="⚖ eBay–AT&T Lawsuit Game")
st.title("⚖ Multiplayer eBay–AT&T Lawsuit Game")

st.markdown("""
**Game Description**  
Two players are matched: **eBay** and **AT&T**.  
- **Nature** decides if eBay is **Guilty** (25%) or **Innocent** (75%).  
- Only eBay knows this.  
- If Guilty → eBay may choose **Generous** or **Stingy**.  
- If Innocent → **Generous** is disabled (must choose Stingy).  
- If Generous → AT&T automatically accepts.  
- If Stingy → AT&T can Accept or Reject.  

**Payoffs** follow the decision tree.
""")

# ---- Firebase Config ----
firebase_key = st.secrets["firebase_key"]
database_url = st.secrets["database_url"]

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(firebase_key))
    firebase_admin.initialize_app(cred, {'databaseURL': database_url})

# ---- Payoff Matrix ----
# Format: payoff_matrix[offer][decision][guilty?] = (ebay_payoff, att_payoff)
payoff_matrix = {
    "Generous": {
        "accept": {"guilty": (-200, 200), "innocent": (-200, 200)}
    },
    "Stingy": {
        "accept": {"guilty": (-20, 20), "innocent": (-20, 20)},
        "reject": {"guilty": (-320, 300), "innocent": (0, -20)}
    }
}

# ---- Join Game ----
name = st.text_input("Enter your name to join:")

if name:
    st.success(f"👋 Welcome, {name}!")
    player_ref = db.reference(f"players/{name}")
    if not player_ref.get():
        player_ref.set({"joined": True, "timestamp": time.time()})
        st.write("✅ Registered in Firebase.")

    match_ref = db.reference("matches")
    match_data = match_ref.get() or {}
    already_matched = False

    # Check if already matched
    for mid, info in match_data.items():
        if name in info.get("players", []):
            role = info["roles"][name]
            match_id = mid
            already_matched = True
            break

    if not already_matched:
        # Try to match
        unmatched = [p for p, v in db.reference("players").get().items()
                     if not any(p in m.get("players", []) for m in match_data.values())
                     and p != name]
        if unmatched:
            partner = unmatched[0]
            pair = sorted([name, partner])
            match_id = f"{pair[0]}_vs_{pair[1]}"
            roles = {pair[0]: "eBay", pair[1]: "AT&T"}
            # Assign guilty/innocent
            guilty_status = random.choices(["guilty", "innocent"], weights=[0.25, 0.75])[0]
            match_ref.child(match_id).set({"players": pair, "roles": roles, "guilty_status": guilty_status})
            role = roles[name]
            already_matched = True
        else:
            st.info("⏳ Waiting for another player...")
            st.stop()

    st.success(f"🎮 You are **{role}** in match `{match_id}`")

    # ---- Game Logic ----
    match_info = match_ref.child(match_id).get()
    guilty_status = match_info["guilty_status"]

    # Stage 1: eBay chooses
    stage1_ref = db.reference(f"games/{match_id}/stage1")
    if role == "eBay":
        st.subheader("Stage 1: Your Offer")
        if guilty_status == "innocent":
            st.info("📢 You are Innocent. You must choose Stingy.")
            offer = "Stingy"
        else:
            offer = st.radio("Choose your offer:", ["Generous", "Stingy"])

        if st.button("Submit Offer"):
            stage1_ref.set({"offer": offer, "guilty_status": guilty_status})
            st.success(f"✅ Offer submitted: {offer}")

    else:
        st.subheader("Stage 1: Waiting for eBay...")
        offer_data = stage1_ref.get()
        if offer_data:
            st.success(f"📢 eBay offered: {offer_data['offer']}")

    # Stage 2: AT&T responds
    offer_data = stage1_ref.get()
    if offer_data:
        offer = offer_data["offer"]
        guilty = offer_data["guilty_status"]

        stage2_ref = db.reference(f"games/{match_id}/stage2")
        if role == "AT&T":
            if offer == "Generous":
                stage2_ref.set({"decision": "accept"})
                st.success("✅ Accepted automatically (Generous offer).")
            else:
                decision = st.radio("Accept or Reject the Stingy offer?", ["accept", "reject"])
                if st.button("Submit Decision"):
                    stage2_ref.set({"decision": decision})
                    st.success(f"✅ Decision submitted: {decision}")
        else:
            st.subheader("Stage 2: Waiting for AT&T...")

        # Show final result if both submitted
        stage2_data = stage2_ref.get()
        if stage2_data:
            decision = stage2_data["decision"]
            ebay_payoff, att_payoff = payoff_matrix[offer][decision][guilty]
            st.subheader("🏆 Final Outcome")
            st.write(f"**eBay payoff:** {ebay_payoff}")
            st.write(f"**AT&T payoff:** {att_payoff}")
            st.balloons()

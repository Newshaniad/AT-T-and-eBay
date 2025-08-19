import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import time
import random
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="⚖️ eBay vs AT&T Classroom Game")

st.title("⚖️ eBay vs AT&T Lawsuit Game")

# Firebase credentials and config
try:
    firebase_key = st.secrets["firebase_key"]
    database_url = st.secrets["database_url"]
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(json.loads(firebase_key))
        firebase_admin.initialize_app(cred, {
            'databaseURL': database_url
        })
except KeyError:
    st.error("🔥 Firebase secrets not configured.")
    st.stop()

# Enhanced chart function
def plot_enhanced_percentage_bar(choices, labels, title, player_type):
    if len(choices) > 0:
        counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100
        
        # Create figure with enhanced styling
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('#f0f0f0')
        ax.set_facecolor('#e0e0e0')
        
        # Color scheme based on player type
        colors_scheme = ['#e74c3c', '#3498db'] if player_type == "eBay" else ['#3498db', '#e74c3c']
        
        # Create bar plot with enhanced styling
        bars = counts.plot(kind='bar', ax=ax, color=colors_scheme, linewidth=2, width=0.7)
        
        # Enhanced styling
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel("Percentage (%)", fontsize=14)
        ax.set_xlabel("Choice", fontsize=14)
        ax.tick_params(rotation=0, labelsize=12)
        ax.set_ylim(0, max(100, counts.max() * 1.1))
        
        # Add grid for better readability
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        # Add value labels on bars
        for i, bar in enumerate(ax.patches):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{height:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        # Add sample size info
        ax.text(0.02, 0.98, f"Sample size: {len(choices)} participants", 
               transform=ax.transAxes, fontsize=10, verticalalignment='top', alpha=0.7,
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # Add current date
        today = datetime.today().strftime('%B %d, %Y')
        ax.text(0.98, 0.98, f"Generated: {today}", transform=ax.transAxes, 
               fontsize=10, verticalalignment='top', horizontalalignment='right', alpha=0.7)
        
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.warning(f"⚠ No data available for {title}")

# Admin section
admin_password = st.text_input("Admin Password:", type="password")

if admin_password == "admin123":
    st.header("🎓 Admin Control Panel")
    
    # Get real-time data
    all_players = db.reference("lawsuit_players").get() or {}
    all_matches = db.reference("lawsuit_matches").get() or {}
    expected_players = db.reference("lawsuit_expected_players").get() or 0
    
    # Calculate statistics
    total_registered = len(all_players)
    ebay_players = [p for p in all_players.values() if p.get("role") == "eBay"]
    att_players = [p for p in all_players.values() if p.get("role") == "AT&T"]
    
    completed_matches = 0
    for match_data in all_matches.values():
        if "ebay_response" in match_data and "att_response" in match_data:
            completed_matches += 1
    
    # Live Statistics Dashboard
    st.subheader("📊 Live Game Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Expected Players", expected_players)
    with col2:
        st.metric("Registered Players", total_registered)
    with col3:
        st.metric("eBay Players", len(ebay_players))
    with col4:
        st.metric("AT&T Players", len(att_players))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Matches", len(all_matches))
    with col2:
        st.metric("Completed Matches", completed_matches)
    with col3:
        guilty_count = len([p for p in ebay_players if p.get("guilt_status") == "Guilty"])
        st.metric("Guilty eBay Players", guilty_count)
    
    # Player activity monitor
    st.subheader("👥 Player Activity Monitor")
    
    if all_players:
        player_status = []
        for name, player_data in all_players.items():
            role = player_data.get("role", "Unknown")
            status = "🔴 Registered"
            activity = "Waiting for match"
            
            # Find player's match
            player_match = None
            for match_id, match_data in all_matches.items():
                if name in [match_data.get("ebay_player"), match_data.get("att_player")]:
                    player_match = match_data
                    break
            
            if player_match:
                if role == "eBay":
                    if "ebay_response" in player_match:
                        status = "🟢 Completed"
                        activity = f"Offered: {player_match['ebay_response']}"
                    else:
                        status = "🟡 In Match"
                        activity = "Making offer..."
                elif role == "AT&T":
                    if "att_response" in player_match:
                        status = "🟢 Completed"
                        activity = f"Response: {player_match['att_response']}"
                    else:
                        status = "🟡 In Match"
                        activity = "Waiting for eBay offer..."
            
            extra_info = ""
            if role == "eBay":
                guilt = player_data.get("guilt_status", "Unknown")
                extra_info = f"({guilt})"
            
            player_status.append({
                "Player Name": name,
                "Role": role,
                "Status": status,
                "Activity": activity,
                "Extra Info": extra_info
            })
        
        status_df = pd.DataFrame(player_status)
        st.dataframe(status_df, use_container_width=True)
    
    # Live analytics
    st.subheader("📈 Live Game Analytics")
    
    if completed_matches > 0:
        # Collect data for charts
        ebay_offers = []
        att_responses = []
        guilt_statuses = []
        
        for match_data in all_matches.values():
            if "ebay_response" in match_data and "att_response" in match_data:
                ebay_offers.append(match_data["ebay_response"])
                att_responses.append(match_data["att_response"])
                guilt_statuses.append(match_data["ebay_guilt"])
        
        col1, col2 = st.columns(2)
        with col1:
            plot_enhanced_percentage_bar(ebay_offers, ["Generous", "Stingy"], "eBay Settlement Offers", "eBay")
            plot_enhanced_percentage_bar(guilt_statuses, ["Guilty", "Innocent"], "eBay Guilt Distribution", "eBay")
        
        with col2:
            plot_enhanced_percentage_bar(att_responses, ["Accept", "Reject"], "AT&T Responses", "AT&T")
            
            # Strategy analysis
            strategies = []
            for match_data in all_matches.values():
                if "ebay_response" in match_data and "att_response" in match_data:
                    guilt = match_data["ebay_guilt"]
                    offer = match_data["ebay_response"]
                    if guilt == "Innocent" and offer == "Stingy":
                        strategies.append("Separating")
                    elif guilt == "Guilty" and offer == "Generous":
                        strategies.append("Separating")
                    else:
                        strategies.append("Pooling")
            
            if strategies:
                plot_enhanced_percentage_bar(strategies, ["Pooling", "Separating"], "eBay Strategy Analysis", "eBay")
    else:
        st.info("No completed matches yet. Charts will appear when players start completing games.")
    
    # Game Configuration
    st.subheader("⚙️ Game Configuration")
    current_expected = db.reference("lawsuit_expected_players").get() or 0
    st.write(f"Current expected players: {current_expected}")
    
    new_expected_players = st.number_input(
        "Set expected number of players:", 
        min_value=0, 
        max_value=100, 
        value=current_expected,
        step=2,
        help="Must be an even number (players are paired)"
    )
    
    if st.button("⚙ Update Expected Players"):
        if new_expected_players % 2 == 0:  # Must be even for pairing
            db.reference("lawsuit_expected_players").set(new_expected_players)
            st.success(f"✅ Expected players set to {new_expected_players}")
            st.rerun()
        else:
            st.error("⚠ Number of players must be even (for pairing)")
    
    # Data management
    st.subheader("🗂️ Data Management")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export Results (CSV)"):
            if completed_matches > 0:
                results_data = []
                for match_id, match_data in all_matches.items():
                    if "ebay_response" in match_data and "att_response" in match_data:
                        # Calculate payoffs with correct values
                        guilt = match_data["ebay_guilt"]
                        offer = match_data["ebay_response"]
                        response = match_data["att_response"]
                        
                        if guilt == "Guilty":
                            if offer == "Generous" and response == "Accept":
                                ebay_payoff, att_payoff = -200, 200
                            elif offer == "Stingy" and response == "Accept":
                                ebay_payoff, att_payoff = -20, 20
                            else:  # Stingy + Reject (Trial)
                                ebay_payoff, att_payoff = -320, 300
                        else:  # Innocent
                            if offer == "Generous" and response == "Accept":
                                ebay_payoff, att_payoff = 0, 0  # Shouldn't happen
                            elif offer == "Stingy" and response == "Accept":
                                ebay_payoff, att_payoff = -20, 20
                            else:  # Stingy + Reject (Trial)
                                ebay_payoff, att_payoff = 0, -20
                        
                        results_data.append({
                            "Match_ID": match_id,
                            "eBay_Player": match_data["ebay_player"],
                            "ATT_Player": match_data["att_player"],
                            "eBay_Status": guilt,
                            "Offer": offer,
                            "Response": response,
                            "eBay_Payoff": ebay_payoff,
                            "ATT_Payoff": att_payoff
                        })
                
                df = pd.DataFrame(results_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name="lawsuit_game_results.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No completed matches to export.")
    
    with col2:
        if st.button("🗑️ Clear All Game Data"):
            db.reference("lawsuit_players").delete()
            db.reference("lawsuit_matches").delete()
            db.reference("lawsuit_expected_players").set(0)
            st.success("🧹 ALL game data cleared!")
            st.rerun()
    
    # Auto-refresh control
    if expected_players > 0 and completed_matches < (expected_players // 2):
        # Auto-refresh while game is active
        time.sleep(3)
        st.rerun()
    elif completed_matches >= (expected_players // 2) and expected_players > 0:
        st.success("🎉 All matches completed! Game finished.")
        if st.button("🔄 Manual Refresh"):
            st.rerun()
    elif st.button("🔄 Refresh Dashboard"):
        st.rerun()
    
    st.divider()
    st.info("👨‍🏫 **Admin Dashboard**: Monitor game progress and analyze results in real-time.")
    
    # Stop here - admin doesn't participate
    st.stop()

# Check if game is configured
if (db.reference("lawsuit_expected_players").get() or 0) <= 0:
    st.info("⚠️ Game not configured yet. Admin needs to set expected number of players.")
    st.stop()

# Game explanation
st.header("📖 Simple Explanation of the Game")

st.markdown("""
This is a **dynamic signaling game** between two players:

🏢 **eBay** (the sender of the signal/offer)  
📡 **AT&T** (the receiver, who decides whether to accept or reject the offer)

### 🎯 What's happening?

1. **Nature decides** whether eBay is **guilty (25%)** or **innocent (75%)**
2. **eBay makes a settlement offer** to AT&T:
   - **Generous offer (G)**
   - **Stingy offer (S)**
3. **If eBay offers generous** → AT&T automatically accepts
4. **If eBay offers stingy** → AT&T chooses to either:
   - **Accept (A)** → no trial
   - **Reject (R)** → go to court

---

### 💰 Payoff Matrix (eBay's payoff, AT&T's payoff):

**If eBay is Guilty (25% probability):**
- Generous → Accept: (-200, 200) *High cost for eBay*
- Stingy → Accept: (-20, 20) *Mild cost for eBay*  
- Stingy → Reject (Trial): (-320, 300) *Very costly for eBay*

**If eBay is Innocent (75% probability):**
- Generous → Not allowed *(Innocent can't signal guilt!)*
- Stingy → Accept: (-20, 20) *Same as guilty case*
- Stingy → Reject (Trial): (0, -20) *AT&T loses failed trial*

### 🎮 Game Steps:

**Step 1**: Player Registration - Enter your name  
**Step 2**: Random Nature Draw - System assigns guilty/innocent (hidden from AT&T)  
**Step 3**: eBay's Move - Choose settlement offer  
**Step 4**: AT&T's Response - Accept or reject stingy offers  
**Step 5**: Show Results - Reveal types, offers, and payoffs  
**Step 6**: Summary Analysis - Class results vs game theory predictions

---
""")

# Player registration
name = st.text_input("Enter your name to join the game:")

if name:
    st.success(f"👋 Welcome, {name}!")
    
    player_ref = db.reference(f"lawsuit_players/{name}")
    player_data = player_ref.get()
    
    if not player_data:
        # Register new player
        player_ref.set({
            "joined": True,
            "timestamp": time.time()
        })
        st.write("✅ You are registered!")
    
    # Check if all expected players registered
    expected_players = db.reference("lawsuit_expected_players").get() or 0
    all_players = db.reference("lawsuit_players").get() or {}
    registered_count = len(all_players)
    
    if registered_count < expected_players:
        st.info(f"⏳ Waiting for more players... ({registered_count}/{expected_players} registered)")
        st.info("🔄 Page will automatically update when all players join.")
        time.sleep(3)
        st.rerun()
    
    # All players registered - start matching process
    st.success(f"🎮 All {expected_players} players registered! Starting the game...")
    
    # Check if player already has role assigned
    existing_player = player_ref.get()
    if not existing_player or "role" not in existing_player:
        # Auto-assign roles fairly
        current_players = db.reference("lawsuit_players").get() or {}
        ebay_count = len([p for p in current_players.values() if p and p.get("role") == "eBay"])
        att_count = len([p for p in current_players.values() if p and p.get("role") == "AT&T"])
        
        # Assign role to balance teams
        if ebay_count < (expected_players // 2):
            role = "eBay"
            # Step 2: Random Nature Draw - Assign guilt status (25% chance of guilty, 75% innocent)
            is_guilty = random.random() < 0.25
            guilt_status = "Guilty" if is_guilty else "Innocent"
            card_color = "🔴 Red Card (Guilty)" if is_guilty else "🔵 Blue Card (Innocent)"
            
            player_ref.update({
                "role": role,
                "guilt_status": guilt_status,
                "card_color": card_color
            })
        else:
            role = "AT&T"
            player_ref.update({"role": role})
    else:
        role = existing_player["role"]
    
    # Display player role
    player_info = player_ref.get()
    if not player_info:
        st.error("Failed to retrieve player information. Please refresh the page.")
        st.stop()
    role = player_info.get("role")
    
    if role == "eBay":
        guilt_status = player_info.get("guilt_status")
        card_color = player_info.get("card_color")
        st.success(f"🏢 **You are eBay (the sender)**")
        if guilt_status and card_color:
            st.info(f"🎴 **Step 2 - Nature's Decision**: {card_color}")
            st.write(f"**Your type is: {guilt_status}** (This information is private - AT&T doesn't know this)")
        else:
            st.warning("Setting up your game info...")
            time.sleep(1)
            st.rerun()
    elif role == "AT&T":
        st.success(f"📡 **You are AT&T (the receiver)**")
        st.info("🎴 You don't know whether eBay is guilty or innocent - you must infer from their offer!")
    else:
        st.warning("Setting up your role...")
        time.sleep(1)
        st.rerun()
    
    # Matching system
    matches_ref = db.reference("lawsuit_matches")
    all_matches = matches_ref.get() or {}
    
    # Check if player already matched
    player_match_id = None
    for match_id, match_data in all_matches.items():
        if name in [match_data.get("ebay_player"), match_data.get("att_player")]:
            player_match_id = match_id
            break
    
    if not player_match_id:
        # Find a match
        all_lawsuit_players = db.reference("lawsuit_players").get() or {}
        
        if role == "eBay":
            # Find an unmatched AT&T player
            unmatched_att_players = []
            for player_name, player_data in all_lawsuit_players.items():
                if player_data.get("role") == "AT&T" and player_name != name:
                    # Check if this AT&T player is already matched
                    already_matched = False
                    for match_data in all_matches.values():
                        if player_name == match_data.get("att_player"):
                            already_matched = True
                            break
                    if not already_matched:
                        unmatched_att_players.append(player_name)
            
            if unmatched_att_players:
                att_partner = unmatched_att_players[0]
                match_id = f"{name}_vs_{att_partner}"
                matches_ref.child(match_id).set({
                    "ebay_player": name,
                    "att_player": att_partner,
                    "ebay_guilt": guilt_status,
                    "timestamp": time.time()
                })
                player_match_id = match_id
                st.success(f"🤝 You are matched with {att_partner}!")
        
        else:  # AT&T player
            # Find an unmatched eBay player
            unmatched_ebay_players = []
            for player_name, player_data in all_lawsuit_players.items():
                if player_data.get("role") == "eBay" and player_name != name:
                    # Check if this eBay player is already matched
                    already_matched = False
                    for match_data in all_matches.values():
                        if player_name == match_data.get("ebay_player"):
                            already_matched = True
                            break
                    if not already_matched:
                        unmatched_ebay_players.append(player_name)
            
            if unmatched_ebay_players:
                ebay_partner = unmatched_ebay_players[0]
                ebay_player_data = all_lawsuit_players[ebay_partner]
                match_id = f"{ebay_partner}_vs_{name}"
                matches_ref.child(match_id).set({
                    "ebay_player": ebay_partner,
                    "att_player": name,
                    "ebay_guilt": ebay_player_data.get("guilt_status"),
                    "timestamp": time.time()
                })
                player_match_id = match_id
                st.success(f"🤝 You are matched with {ebay_partner}!")
    
    if not player_match_id:
        st.info("⏳ Waiting for a match partner...")
        time.sleep(2)
        st.rerun()
    
    # Game play
    match_ref = matches_ref.child(player_match_id)
    match_data = match_ref.get()
    
    if role == "eBay":
        st.subheader("💼 Step 3: eBay's Move - Make Your Settlement Offer")
        
        if "ebay_response" not in match_data:
            guilt_status = match_data["ebay_guilt"]
            
            st.write(f"**Reminder**: You are {guilt_status}")
            
            if guilt_status == "Innocent":
                st.warning("⚠️ **Game Rule**: Innocent eBay is forced to offer Stingy (to simplify the strategy set)")
                st.info("💡 **Strategic Note**: If you could offer Generous, it might signal guilt!")
                offer_options = ["Stingy"]
            else:  # Guilty
                st.info("💰 **Your Choice**: As a guilty party, you can choose either offer type")
                offer_options = ["Generous", "Stingy"]
            
            offer = st.radio("Choose your settlement offer:", offer_options, 
                           help="Generous = High settlement amount, Stingy = Low settlement amount")
            
            if st.button("Submit Offer"):
                match_ref.update({
                    "ebay_response": offer,
                    "ebay_timestamp": time.time()
                })
                st.success(f"✅ You offered a {offer} settlement!")
                st.rerun()
        else:
            st.success(f"✅ You already submitted: {match_data['ebay_response']} offer")
            st.info("⏳ Waiting for AT&T's response...")
            
            # Auto-refresh to check for AT&T response
            if "att_response" not in match_data:
                time.sleep(2)
                st.rerun()
    
    elif role == "AT&T":
        st.subheader("📡 Step 4: AT&T's Response - Accept or Reject")
        
        if "ebay_response" not in match_data:
            st.info("⏳ Waiting for eBay to make an offer...")
            time.sleep(2)
            st.rerun()
        
        elif "att_response" not in match_data:
            ebay_offer = match_data["ebay_response"]
            ebay_player = match_data["ebay_player"]
            
            st.info(f"💼 **{ebay_player} offered a {ebay_offer} settlement**")
            
            if ebay_offer == "Generous":
                st.success("💰 **Game Rule**: Generous offers are automatically accepted!")
                st.write("🤔 **Think**: What does this generous offer tell you about eBay's type?")
                response = "Accept"
                auto_accept = True
            else:  # Stingy
                st.write("🤔 **Strategic Decision**: You received a stingy offer. What should you infer?")
                st.info("💡 **Think**: Could this be from a guilty or innocent eBay? What are the probabilities?")
                response = st.radio("What do you do?", ["Accept", "Reject (Go to Court)"],
                                  help="Accept = Take the low settlement, Reject = Go to expensive trial")
                auto_accept = False
            
            if st.button("Submit Response") or auto_accept:
                response_final = "Accept" if response == "Accept" else "Reject"
                match_ref.update({
                    "att_response": response_final,
                    "att_timestamp": time.time()
                })
                st.success(f"✅ You chose to {response_final}!")
                st.rerun()
        else:
            st.success(f"✅ You responded: {match_data['att_response']}")
    
    # Show results when both completed
    if "ebay_response" in match_data and "att_response" in match_data:
        st.header("🎯 Step 5: Results - The Truth is Revealed!")
        
        ebay_player = match_data["ebay_player"]
        att_player = match_data["att_player"]
        guilt = match_data["ebay_guilt"]
        offer = match_data["ebay_response"]
        response = match_data["att_response"]
        
        # Show the revelation
        st.subheader("🔍 What Really Happened:")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**eBay's Type**\n{guilt}")
        with col2:
            st.info(f"**eBay's Offer**\n{offer}")
        with col3:
            st.info(f"**AT&T's Response**\n{response}")
        
        # Calculate payoffs based on correct payoff matrix
        if guilt == "Guilty":
            if offer == "Generous" and response == "Accept":
                ebay_payoff, att_payoff = -200, 200
            elif offer == "Stingy" and response == "Accept":
                ebay_payoff, att_payoff = -20, 20
            else:  # Stingy + Reject (Trial)
                ebay_payoff, att_payoff = -320, 300
        else:  # Innocent
            if offer == "Generous" and response == "Accept":
                # This shouldn't happen since innocent can't offer generous
                ebay_payoff, att_payoff = 0, 0  
            elif offer == "Stingy" and response == "Accept":
                ebay_payoff, att_payoff = -20, 20
            else:  # Stingy + Reject (Trial)
                ebay_payoff, att_payoff = 0, -20
        
        # Show payoffs with explanation
        st.subheader("💰 Final Payoffs:")
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"**eBay ({ebay_player})**\nPayoff: {ebay_payoff}")
        with col2:
            st.success(f"**AT&T ({att_player})**\nPayoff: {att_payoff}")
        
        # Outcome explanation
        if response == "Reject":
            st.write("⚖️ **Outcome**: Went to court! Both sides paid legal fees.")
            if guilt == "Guilty":
                st.write("🔍 **Court Result**: eBay was found guilty and paid damages plus legal costs")
            else:
                st.write("🔍 **Court Result**: eBay was found innocent - AT&T paid all legal costs!")
        else:
            st.write("🤝 **Outcome**: Settled out of court - no legal fees!")
            st.write(f"💸 **Settlement**: AT&T accepted the {offer.lower()} offer")
        
        st.balloons()
        st.success("✅ Your match is complete! Thank you for playing.")
        
        # Check if all matches completed for results display
        expected_players = db.reference("lawsuit_expected_players").get() or 0
        all_matches = db.reference("lawsuit_matches").get() or {}
        completed_matches = 0
        for match_data in all_matches.values():
            if "ebay_response" in match_data and "att_response" in match_data:
                completed_matches += 1
        
        expected_matches = expected_players // 2
        
        if completed_matches >= expected_matches:
            st.header("📊 Step 6: Summary Analysis - Class Results vs Game Theory")
            
            # Collect all results
            ebay_offers = []
            att_responses = []
            guilt_statuses = []
            guilty_offers = []
            innocent_offers = []
            stingy_responses = []
            
            for match_data in all_matches.values():
                if "ebay_response" in match_data and "att_response" in match_data:
                    guilt = match_data["ebay_guilt"]
                    offer = match_data["ebay_response"]
                    response = match_data["att_response"]
                    
                    ebay_offers.append(offer)
                    att_responses.append(response)
                    guilt_statuses.append(guilt)
                    
                    # Separate by guilt status
                    if guilt == "Guilty":
                        guilty_offers.append(offer)
                    else:
                        innocent_offers.append(offer)
                    
                    # AT&T responses to stingy offers only
                    if offer == "Stingy":
                        stingy_responses.append(response)
            
            # Show key visualization as requested
            st.subheader("🎯 Key Strategic Analysis")
            
            col1, col2 = st.columns(2)
            with col1:
                # % of guilty vs innocent choosing Stingy
                if guilty_offers and innocent_offers:
                    guilty_stingy = len([o for o in guilty_offers if o == "Stingy"])
                    innocent_stingy = len([o for o in innocent_offers if o == "Stingy"])
                    
                    guilty_stingy_pct = guilty_stingy / len(guilty_offers) * 100
                    innocent_stingy_pct = innocent_stingy / len(innocent_offers) * 100
                    
                    fig, ax = plt.subplots(figsize=(8, 5))
                    categories = ['Guilty eBay', 'Innocent eBay']
                    percentages = [guilty_stingy_pct, innocent_stingy_pct]
                    colors = ['#e74c3c', '#2ecc71']
                    
                    bars = ax.bar(categories, percentages, color=colors, alpha=0.8)
                    ax.set_title("% Choosing Stingy Offer by eBay Type", fontsize=14, fontweight='bold')
                    ax.set_ylabel("Percentage (%)")
                    ax.set_ylim(0, 110)
                    
                    # Add value labels
                    for bar, pct in zip(bars, percentages):
                        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                               f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
                    
                    ax.grid(True, alpha=0.3)
                    plt.tight_layout()
                    st.pyplot(fig)
                else:
                    st.info("Need both guilty and innocent players to show this analysis")
            
            with col2:
                # % of AT&T accepting stingy offers
                if stingy_responses:
                    accept_stingy = len([r for r in stingy_responses if r == "Accept"])
                    accept_pct = accept_stingy / len(stingy_responses) * 100
                    
                    fig, ax = plt.subplots(figsize=(8, 5))
                    categories = ['Accept', 'Reject']
                    accept_count = len([r for r in stingy_responses if r == "Accept"])
                    reject_count = len([r for r in stingy_responses if r == "Reject"])
                    
                    values = [accept_count, reject_count]
                    percentages_vals = [v/len(stingy_responses)*100 for v in values]
                    colors = ['#3498db', '#e74c3c']
                    
                    bars = ax.bar(categories, percentages_vals, color=colors, alpha=0.8)
                    ax.set_title("AT&T Responses to Stingy Offers", fontsize=14, fontweight='bold')
                    ax.set_ylabel("Percentage (%)")
                    ax.set_ylim(0, 110)
                    
                    # Add value labels
                    for bar, pct in zip(bars, percentages_vals):
                        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                               f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold')
                    
                    ax.grid(True, alpha=0.3)
                    plt.tight_layout()
                    st.pyplot(fig)
                else:
                    st.info("No stingy offers made yet")
            
            # Game Theory Analysis
            st.subheader("🧮 Game Theory Predictions vs Your Class")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if stingy_responses:
                    accept_stingy_pct = len([r for r in stingy_responses if r == "Accept"]) / len(stingy_responses) * 100
                    st.metric("AT&T Accept Stingy Offers", f"{accept_stingy_pct:.1f}%", "Theory: 40%")
                else:
                    st.metric("AT&T Accept Stingy Offers", "N/A", "Theory: 40%")
            
            with col2:
                if guilty_offers:
                    guilty_stingy_pct = len([o for o in guilty_offers if o == "Stingy"]) / len(guilty_offers) * 100
                    st.metric("Guilty eBay Choose Stingy", f"{guilty_stingy_pct:.1f}%", "Theory: ~43%")
                else:
                    st.metric("Guilty eBay Choose Stingy", "N/A", "Theory: ~43%")
            
            with col3:
                if innocent_offers:
                    innocent_stingy_pct = len([o for o in innocent_offers if o == "Stingy"]) / len(innocent_offers) * 100
                    st.metric("Innocent eBay Choose Stingy", f"{innocent_stingy_pct:.1f}%", "Theory: 100%")
                else:
                    st.metric("Innocent eBay Choose Stingy", "N/A", "Theory: 100%")
            
            # Bayesian Analysis
            st.subheader("🔍 Bayesian Analysis")
            if stingy_responses:
                st.info(f"""
                **Key Insight**: When you see a **Stingy** offer, what's the probability eBay is guilty?
                
                **Your Class Results**: 
                - {len(stingy_responses)} stingy offers were made
                - AT&T accepted {len([r for r in stingy_responses if r == "Accept"])} of them ({accept_stingy_pct:.1f}%)
                
                **Theoretical Prediction**: 
                - P(Guilty | Stingy Offer) ≈ 12.5% 
                - Most stingy offers actually come from innocent parties!
                """)
            
            st.success("🎉 **Dynamic Signaling Game Complete!** You've experienced Nash Equilibrium, Bayesian updating, and strategic signaling in action!")

# Show game status
st.sidebar.header("🎮 Game Status")
players = db.reference("lawsuit_players").get() or {}
expected = db.reference("lawsuit_expected_players").get() or 0
registered = len(players)

st.sidebar.write(f"**Players**: {registered}/{expected}")

if expected > 0:
    progress = min(registered / expected, 1.0)
    st.sidebar.progress(progress)

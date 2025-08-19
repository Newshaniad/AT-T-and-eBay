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
                        # Calculate payoffs
                        guilt = match_data["ebay_guilt"]
                        offer = match_data["ebay_response"]
                        response = match_data["att_response"]
                        
                        if guilt == "Guilty":
                            if offer == "Generous" and response == "Accept":
                                ebay_payoff, att_payoff = -100, 100
                            elif offer == "Stingy" and response == "Accept":
                                ebay_payoff, att_payoff = -20, 20
                            else:  # Stingy + Reject
                                ebay_payoff, att_payoff = -200, 100
                        else:  # Innocent
                            if offer == "Generous" and response == "Accept":
                                ebay_payoff, att_payoff = -80, 100
                            elif offer == "Stingy" and response == "Accept":
                                ebay_payoff, att_payoff = -10, 20
                            else:  # Stingy + Reject
                                ebay_payoff, att_payoff = 0, -100
                        
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

# Game description
st.markdown("""
### 🎭 The Legal Drama

**AT&T sues eBay for patent infringement.**

- Sometimes eBay is **guilty**, sometimes **innocent** (25% chance of guilty)
- eBay can make a **generous offer** or **stingy offer** to settle
- If **generous**, AT&T automatically accepts (who wouldn't want more money?)
- If **stingy**, AT&T can **accept** or **reject and go to court**
- **Court costs both sides money** - lawyers are expensive!
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
    if "role" not in existing_player:
        # Auto-assign roles fairly
        current_players = db.reference("lawsuit_players").get() or {}
        ebay_count = len([p for p in current_players.values() if p.get("role") == "eBay"])
        att_count = len([p for p in current_players.values() if p.get("role") == "AT&T"])
        
        # Assign role to balance teams
        if ebay_count < (expected_players // 2):
            role = "eBay"
            # Assign guilt status (25% chance of guilty)
            is_guilty = random.random() < 0.25
            guilt_status = "Guilty" if is_guilty else "Innocent"
            card_color = "🔴 Red Card" if is_guilty else "🔵 Blue Card"
            
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
    role = player_info["role"]
    
    if role == "eBay":
        guilt_status = player_info["guilt_status"]
        card_color = player_info["card_color"]
        st.success(f"🎴 You are **eBay** - {card_color} - You are **{guilt_status}**")
    else:
        st.success(f"🏢 You are **AT&T**")
    
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
        st.subheader("💼 eBay: Make Your Settlement Offer")
        
        if "ebay_response" not in match_data:
            guilt_status = match_data["ebay_guilt"]
            
            if guilt_status == "Innocent":
                st.warning("⚠️ **Rule**: As an innocent party, you cannot make a Generous offer (it would look suspicious!)")
                offer_options = ["Stingy"]
            else:  # Guilty
                offer_options = ["Generous", "Stingy"]
            
            offer = st.radio("Choose your settlement offer:", offer_options)
            
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
        st.subheader("🏢 AT&T: Respond to eBay's Offer")
        
        if "ebay_response" not in match_data:
            st.info("⏳ Waiting for eBay to make an offer...")
            time.sleep(2)
            st.rerun()
        
        elif "att_response" not in match_data:
            ebay_offer = match_data["ebay_response"]
            ebay_player = match_data["ebay_player"]
            
            st.info(f"💼 {ebay_player} offered a **{ebay_offer}** settlement")
            
            if ebay_offer == "Generous":
                st.success("💰 It's generous! You automatically Accept!")
                response = "Accept"
                auto_accept = True
            else:  # Stingy
                response = st.radio("What do you do?", ["Accept", "Reject (Go to Court)"])
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
        st.header("🎯 Match Results")
        
        ebay_player = match_data["ebay_player"]
        att_player = match_data["att_player"]
        guilt = match_data["ebay_guilt"]
        offer = match_data["ebay_response"]
        response = match_data["att_response"]
        
        # Calculate payoffs
        if guilt == "Guilty":
            if offer == "Generous" and response == "Accept":
                ebay_payoff, att_payoff = -100, 100
            elif offer == "Stingy" and response == "Accept":
                ebay_payoff, att_payoff = -20, 20
            else:  # Stingy + Reject
                ebay_payoff, att_payoff = -200, 100
        else:  # Innocent
            if offer == "Generous" and response == "Accept":
                ebay_payoff, att_payoff = -80, 100
            elif offer == "Stingy" and response == "Accept":
                ebay_payoff, att_payoff = -10, 20
            else:  # Stingy + Reject
                ebay_payoff, att_payoff = 0, -100
        
        st.success(f"**Final Outcome:**")
        st.write(f"- **eBay** ({ebay_player}): {guilt}, offered {offer} → Payoff: **{ebay_payoff}**")
        st.write(f"- **AT&T** ({att_player}): {response} → Payoff: **{att_payoff}**")
        
        if response == "Reject":
            st.write("⚖️ **Went to court!**")
        else:
            st.write("🤝 **Settled out of court!**")
        
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
            st.header("📊 Game Summary - All Matches Complete!")
            
            # Collect all results
            ebay_offers = []
            att_responses = []
            guilt_statuses = []
            
            for match_data in all_matches.values():
                if "ebay_response" in match_data and "att_response" in match_data:
                    ebay_offers.append(match_data["ebay_response"])
                    att_responses.append(match_data["att_response"])
                    guilt_statuses.append(match_data["ebay_guilt"])
            
            # Show final charts
            col1, col2 = st.columns(2)
            with col1:
                plot_enhanced_percentage_bar(ebay_offers, ["Generous", "Stingy"], "Final: eBay Settlement Offers", "eBay")
                plot_enhanced_percentage_bar(guilt_statuses, ["Guilty", "Innocent"], "Final: eBay Guilt Distribution", "eBay")
            
            with col2:
                plot_enhanced_percentage_bar(att_responses, ["Accept", "Reject"], "Final: AT&T Responses", "AT&T")
                
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
                    plot_enhanced_percentage_bar(strategies, ["Pooling", "Separating"], "Final: eBay Strategy Analysis", "eBay")
            
            # Show theoretical comparison
            st.subheader("🧮 Theory vs Reality")
            pooling_count = len([s for s in strategies if s == "Pooling"])
            pooling_pct = pooling_count / len(strategies) * 100 if strategies else 0
            
            accept_count = len([r for r in att_responses if r == "Accept"])
            accept_pct = accept_count / len(att_responses) * 100 if att_responses else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Your Class: eBay Pooling", f"{pooling_pct:.1f}%", "Theory: 42.9%")
            with col2:
                st.metric("Your Class: AT&T Accept Stingy", f"{accept_pct:.1f}%", "Theory: 40.0%")
            
            st.success("🎉 **Game Complete!** You've experienced Nash Equilibrium and game theory in action!")

# Show game status
st.sidebar.header("🎮 Game Status")
players = db.reference("lawsuit_players").get() or {}
expected = db.reference("lawsuit_expected_players").get() or 0
registered = len(players)

st.sidebar.write(f"**Players**: {registered}/{expected}")

if expected > 0:
    progress = min(registered / expected, 1.0)
    st.sidebar.progress(progress)

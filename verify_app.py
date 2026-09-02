import sys
# pyrefly: ignore [missing-import,wildcard-import]
from streamlit.testing.v1 import AppTest

def verify_app():
    print("Initializing AppTest...")
    at = AppTest.from_file("app.py", default_timeout=30).run()
    
    if at.exception:
        print("EXCEPTION IN APP:")
        for e in at.exception:
            print(e.message)
            print(e.stack_trace)
        return
        
    print("\n--- SCREEN 1: QUEUE (Default) ---")
    print("Tabs available:", [t.label for t in at.tabs])
    
    # Find dataframes in the first tab
    queue_tab = at.tabs[0]
    print("Dataframes on Queue screen:")
    for i, df_el in enumerate(queue_tab.dataframe):
        df = df_el.value
        print(f"  DF {i} columns: {list(df.columns)}")
        print(f"  DF {i} length: {len(df)}")
        if len(df) > 0:
            print(f"  DF {i} sample row: {df.iloc[0].to_dict()}")
            
    print("Buttons:", [b.label for b in queue_tab.button])
    print("Selectboxes:", [s.label for s in queue_tab.selectbox])
    
    dispute_selectbox = next(s for s in queue_tab.selectbox if "Select a Dispute" in s.label)
    if len(dispute_selectbox.options) > 1:
        # Get the first actual dispute ID
        selected_dispute = [opt for opt in dispute_selectbox.options if opt][0]
        print(f"\nSelecting dispute {selected_dispute}...")
        dispute_selectbox.set_value(selected_dispute).run()
        
        view_btn = next(b for b in queue_tab.button if b.label == "View Detail")
        print("Clicking 'View Detail'...")
        view_btn.click().run()
        
        if at.exception:
            print("EXCEPTION IN APP:", at.exception[0].message)
            return
            
        print("\n--- SCREEN 2: DETAIL ---")
        queue_tab_updated = at.tabs[0]
        print("Headers/Subheaders:")
        for h in queue_tab_updated.header: print(f"  Header: {h.value}")
        for sh in queue_tab_updated.subheader: print(f"  Subheader: {sh.value}")
        
        print("\nMarkdown blocks (sample):")
        md_texts = [md.value for md in queue_tab_updated.markdown]
        for md in md_texts[:5]: 
            print(f"  MD: {md}")
            
        print("\nButtons on Detail:")
        for b in queue_tab_updated.button: print(f"  Button: {b.label}")
            
        print("\nClicking '← Back to queue'...")
        back_btn = next(b for b in queue_tab_updated.button if "Back to queue" in b.label)
        back_btn.click().run()
        
    print("\n--- SCREEN 3: METRICS ---")
    metrics_tab = at.tabs[1]
    
    print("Metrics cards:")
    for m in metrics_tab.metric:
        print(f"  {m.label} = {m.value}")
        
    print("Dataframes on Metrics screen:")
    for df_el in metrics_tab.dataframe:
        df = df_el.value
        print(f"  DF columns: {list(df.columns)}, length: {len(df)}")
        if len(df) > 0:
            print(f"  DF sample row: {df.iloc[0].to_dict()}")

if __name__ == '__main__':
    verify_app()

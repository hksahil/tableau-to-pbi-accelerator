import streamlit as st
import xml.etree.ElementTree as ET

def create_datasource_map(file):
    tree = ET.parse(file)
    root = tree.getroot()

    # Create a mapping of datasource names to their captions
    datasource_map = {}
    for datasource in root.findall(".//datasource"):
        datasource_name = datasource.get('name')
        datasource_caption = datasource.get('caption')
        if datasource_name and datasource_caption:
            datasource_map[datasource_name] = datasource_caption
    
    return datasource_map

def main():
    st.title("Tableau XML Metadata Extractor")
    
    uploaded_file = st.file_uploader("Upload a Tableau XML file", type="xml")
    
    if uploaded_file is not None:
        # Create and display the datasource map
        datasource_map = create_datasource_map(uploaded_file)
        st.write("Datasource Map (Name -> Caption):")
        st.write(datasource_map)
        
        # If needed, you can also use this map in further processing
        
if __name__ == "__main__":
    main()

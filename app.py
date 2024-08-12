import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

def parse_tableau_xml(file):
    tree = ET.parse(file)
    root = tree.getroot()
    
    # Initialize lists to store the data
    data = []
    
    # Create a mapping of worksheets to dashboards
    dashboard_map = {}

    # Iterate through all dashboards to find their worksheets
    for dashboard in root.findall(".//dashboards//dashboard"):
        dashboard_name = dashboard.get('name')
        for zone in dashboard.findall(".//zone"):
            worksheet_name = zone.get('name')
            if worksheet_name:
                dashboard_map[worksheet_name] = dashboard_name

    # Iterate through all worksheets and extract associated dashboard names
    for worksheet in root.findall(".//worksheet"):
        worksheet_name = worksheet.get('name')
        
        # Get the dashboard name from the map
        dashboard_name = dashboard_map.get(worksheet_name, "No Dashboard")
        
        # Find the associated data source
        data_source = None
        columns = []
        for datasource in root.findall(".//datasource"):
            for dependency in worksheet.findall(".//datasource-dependencies[@datasource='" + datasource.get('name') + "']"):
                data_source = datasource.get('caption')
                for column in dependency.findall(".//column"):
                    column_caption = column.get('caption')
                    if column_caption:  # Only append non-None captions
                        columns.append(column_caption)
        
        # Append data to the list
        data.append({
            "Dashboard Name": dashboard_name,
            "Worksheet Name": worksheet_name,
            "Data Source": data_source if data_source else "No Data Source",
            "Columns": ", ".join(columns) if columns else "No Columns"
        })
    
    # Convert the list to a DataFrame
    df = pd.DataFrame(data)
    return df

def main():
    st.title("Tableau XML Metadata Extractor")
    
    uploaded_file = st.file_uploader("Upload a Tableau XML file", type="xml")
    
    if uploaded_file is not None:
        # Parse the XML and extract the metadata
        df = parse_tableau_xml(uploaded_file)
        
        # Display the DataFrame
        st.dataframe(df)
        
        # Option to download the data as CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "tableau_metadata.csv", "text/csv", key='download-csv')
        
if __name__ == "__main__":
    main()

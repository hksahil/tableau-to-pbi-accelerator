import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

def parse_tableau_xml(file):
    tree = ET.parse(file)
    root = tree.getroot()
    
    # Initialize lists to store the data
    data = []
    
    # Create a mapping of datasource names to their captions
    datasource_map = {}
    for datasource in root.findall(".//datasource"):
        datasource_name = datasource.get('name')
        datasource_caption = datasource.get('caption')
        if datasource_name and datasource_caption:
            datasource_map[datasource_name] = datasource_caption
    
    # Create a mapping of columns to their captions
    column_map = {}
    for column in root.findall(".//column"):
        column_name = column.get('name')
        column_caption = column.get('caption')
        if column_name and column_caption:
            column_map[column_name] = column_caption
    
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
        
        # Find the associated data source, used columns, and slices (filters)
        data_source_caption = "No Data Source"
        columns = []
        slices = []
        
        # Extract data source and columns
        for datasource_dep in worksheet.findall(".//datasource-dependencies"):
            datasource_name = datasource_dep.get('datasource')
            # Use the map to get the caption
            data_source_caption = datasource_map.get(datasource_name, datasource_name)
            for column in datasource_dep.findall(".//column"):
                column_name = column.get('name')
                # Replace with the column caption if available
                column_caption = column_map.get(column_name, column_name)
                columns.append(column_caption)
        
        # Collect slices applied on the worksheet and replace datasource names with captions
        for slice_element in worksheet.findall(".//slices/column"):
            slice_text = slice_element.text
            if slice_text:
                # Replace the datasource name with its caption in the slice
                for datasource_name, caption in datasource_map.items():
                    if slice_text.startswith(f"[{datasource_name}]."):
                        slice_text = slice_text.replace(f"[{datasource_name}].", f"[{caption}].")
                slices.append(slice_text)
        
        # Append data to the list
        data.append({
            "Dashboard Name": dashboard_name,
            "Worksheet Name": worksheet_name,
            "Data Source": data_source_caption,
            "Columns": ", ".join(columns) if columns else "No Columns",
            "Slices": ", ".join(slices) if slices else "No Slices"
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

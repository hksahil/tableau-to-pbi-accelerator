import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import re

def normalize_column_name(name):
    # Check if the name is None, return an empty string or a placeholder if it is
    if name is None:
        return ""
    # Normalize the column name by removing brackets and trimming spaces
    return re.sub(r'[\[\]]', '', name).strip()

def replace_internal_names_with_captions(formula, column_map):
    # Replace the internal names with their corresponding captions in the formula
    if formula is None:
        return "No Formula"
    for internal_name, caption in column_map.items():
        normalized_internal_name = f"[{internal_name}]"
        if normalized_internal_name in formula:
            formula = formula.replace(normalized_internal_name, caption)
    return formula

def parse_tableau_xml(file):
    tree = ET.parse(file)
    root = tree.getroot()
    
    # Initialize lists to store the data
    worksheet_data = []
    datasource_data = []
    
    # Create a mapping of datasource names to their captions
    datasource_map = {}
    for datasource in root.findall(".//datasource"):
        datasource_name = datasource.get('name')
        datasource_caption = datasource.get('caption')
        if datasource_name and datasource_caption:
            datasource_map[datasource_name] = datasource_caption
    
    # Create a mapping of columns to their captions, datatypes, and formulas
    column_map = {}
    column_type_map = {}
    column_formula_map = {}
    for column in root.findall(".//column"):
        column_name = normalize_column_name(column.get('name'))
        column_caption = column.get('caption')
        column_datatype = column.get('datatype')
        column_formula = column.find("./calculation")
        if column_name:
            column_map[column_name] = column_caption or column_name
            column_type_map[column_name] = column_datatype or "Unknown"
            if column_formula is not None:
                column_formula_map[column_name] = replace_internal_names_with_captions(
                    column_formula.get('formula'), column_map)
            else:
                column_formula_map[column_name] = "No Formula"
    
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
                column_name = normalize_column_name(column.get('name'))
                # Replace with the column caption if available
                column_caption = column_map.get(column_name, column_name)
                columns.append(column_caption)
        
        # Collect slices applied on the worksheet and replace datasource names with captions
        for slice_element in worksheet.findall(".//slices/column"):
            slice_text = slice_element.text
            if slice_text:
                # Normalize the slice column name and replace the datasource name with its caption in the slice
                for datasource_name, caption in datasource_map.items():
                    normalized_datasource_name = normalize_column_name(datasource_name)
                    if slice_text.startswith(f"[{normalized_datasource_name}]."):
                        slice_text = slice_text.replace(f"[{normalized_datasource_name}].", f"[{caption}].")
                slices.append(slice_text)
        
        # Append worksheet data to the list
        worksheet_data.append({
            "Dashboard Name": dashboard_name,
            "Worksheet Name": worksheet_name,
            "Data Source": data_source_caption,
            "Columns": ", ".join(columns) if columns else "No Columns",
            "Slices": ", ".join(slices) if slices else "No Slices"
        })
    
    # Extract data for datasource DataFrame
    seen_columns = set()
    for datasource_name, caption in datasource_map.items():
        for column_name, column_caption in column_map.items():
            column_datatype = column_type_map.get(column_name, "Unknown")
            column_formula = column_formula_map.get(column_name, "No Formula")
            normalized_column_name = normalize_column_name(column_name)
            if normalized_column_name and normalized_column_name not in seen_columns:
                datasource_data.append({
                    "Datasource Caption": caption,
                    "Column Name": column_caption,
                    "Column Datatype": column_datatype,
                    "Formula": column_formula
                })
                seen_columns.add(normalized_column_name)

    # Convert the lists to DataFrames
    worksheet_df = pd.DataFrame(worksheet_data)
    datasource_df = pd.DataFrame(datasource_data)
    
    return worksheet_df, datasource_df

def main():
    st.title("Tableau XML Metadata Extractor")
    
    uploaded_file = st.file_uploader("Upload a Tableau XML file", type="xml")
    
    if uploaded_file is not None:
        # Parse the XML and extract the metadata
        worksheet_df, datasource_df = parse_tableau_xml(uploaded_file)
        
        # Display the DataFrames
        st.subheader("Worksheet Data")
        st.dataframe(worksheet_df)
        
        st.subheader("Datasource Data")
        st.dataframe(datasource_df)
        
        # Option to download the data as CSV
        worksheet_csv = worksheet_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Worksheet Data as CSV", worksheet_csv, "tableau_worksheet_metadata.csv", "text/csv", key='download-worksheet-csv')
        
        datasource_csv = datasource_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Datasource Data as CSV", datasource_csv, "tableau_datasource_metadata.csv", "text/csv", key='download-datasource-csv')
        
if __name__ == "__main__":
    main()

import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import re
#import openai

# Set your OpenAI API key
#openai.api_key = 'your-api-key'

dashboard_filters_count = 0



def convert_to_dax_expression(expression):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Convert the following tableau formula to a DAX expression and provide only the DAX code without any explanation: {expression}"}
            ],
            max_tokens=100
        )
        dax_expression = response.choices[0].message['content'].strip()
    except Exception as e:
        dax_expression = f"Error: {str(e)}"
    return dax_expression

def process_dataframe(df):
    df['powerbi formula'] = None
    for index, row in df.iterrows():
        if row['Formula'] != 'No Formula':
            expression = row['Formula']
            dax_expression = convert_to_dax_expression(expression)
            df.at[index, 'powerbi formula'] = dax_expression
    return df

def normalize_column_name(name):
    if name is None:
        return ""
    return re.sub(r'[\[\]]', '', name).strip()

def replace_internal_names_with_captions(formula, column_map):
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
    
    workbook_name_element = root.find(".//repository-location")
    workbook_name = "Unknown Workbook"
    if workbook_name_element is not None:
        workbook_id = workbook_name_element.get('id', '')
        workbook_name = '_'.join(workbook_id.split('_')[:-1]) if '_' in workbook_id else workbook_id
        
    worksheet_data = []
    datasource_data = []
    dashboard_names = set()
    worksheet_count = 0
    calculated_column_count = 0
    dashboard_filters_count = 0
    
    datasource_map = {}
    for datasource in root.findall(".//datasource"):
        datasource_name = datasource.get('name')
        datasource_caption = datasource.get('caption')
        if datasource_name and datasource_caption:
            datasource_map[datasource_name] = datasource_caption
    
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
    
    def replace_internal_with_caption(text, column_map):
        for internal_name, caption in column_map.items():
            text = text.replace(f"[{internal_name}]", f"[{caption}]")
        return text


    dashboard_map = {}
    for dashboard in root.findall(".//dashboards//dashboard"):
        dashboard_name = dashboard.get('name')
        dashboard_names.add(dashboard_name)
        for datasource_dep in dashboard.findall(".//datasource-dependencies"):
            dashboard_filters_count += len(datasource_dep.findall(".//column"))
        for zone in dashboard.findall(".//zone"):
            worksheet_name = zone.get('name')
            if worksheet_name:
                dashboard_map[worksheet_name] = dashboard_name
    
    for worksheet in root.findall(".//worksheet"):
        worksheet_count +=1
        worksheet_name = worksheet.get('name')
        dashboard_name = dashboard_map.get(worksheet_name, "No Dashboard")
        data_source_caption = "No Data Source"
        columns = []
        slices = []
        
        worksheet_title = "No Title"
        title_element = worksheet.find(".//title/formatted-text/run")
        if title_element is not None and title_element.text:
            worksheet_title = title_element.text.strip()
        
        for datasource_dep in worksheet.findall(".//datasource-dependencies"):
            datasource_name = datasource_dep.get('datasource')
            data_source_caption = datasource_map.get(datasource_name, datasource_name)
            for column in datasource_dep.findall(".//column"):
                column_name = normalize_column_name(column.get('name'))
                column_caption = column_map.get(column_name, column_name)
                columns.append(column_caption)
        
        for slice_element in worksheet.findall(".//slices/column"):
            slice_text = slice_element.text
            if slice_text:
                for datasource_name, caption in datasource_map.items():
                    normalized_datasource_name = normalize_column_name(datasource_name)
                    if slice_text.startswith(f"[{normalized_datasource_name}]."):
                        slice_text = slice_text.replace(f"[{normalized_datasource_name}].", f"[{caption}].")
                slices.append(slice_text)
        
        rows_data = []
        cols_data = []
        
        for row_element in worksheet.findall(".//rows"):
            row_text = row_element.text
            if row_text:
                row_text = replace_internal_names_with_captions(row_text, column_map)
                for datasource_name, caption in datasource_map.items():
                    row_text = row_text.replace(f"[{datasource_name}].", f"[{caption}].")
                row_text = replace_internal_with_caption(row_text, column_map)
                rows_data.append(normalize_column_name(row_text))
        
        for col_element in worksheet.findall(".//cols"):
            col_text = col_element.text
            if col_text:
                col_text = replace_internal_names_with_captions(col_text, column_map)
                for datasource_name, caption in datasource_map.items():
                    col_text = col_text.replace(f"[{datasource_name}].", f"[{caption}].")
                col_text = replace_internal_with_caption(col_text, column_map)
                cols_data.append(normalize_column_name(col_text))
        
        mark_element = worksheet.find(".//mark")
        chart_type = "Unknown"
        if mark_element is not None and 'class' in mark_element.attrib:
            chart_type = mark_element.attrib['class']
        
        worksheet_data.append({
            "Workbook Name": workbook_name,
            "Dashboard Name": dashboard_name,
            "Worksheet Name": worksheet_name,
            "Worksheet Title": worksheet_title,
            "Data Source": data_source_caption,
            "Slices": ", ".join(slices) if slices else "No Slices",
            "Rows": ", ".join(rows_data) if rows_data else "No Rows",
            "Columns": ", ".join(cols_data) if cols_data else "No Columns",
            "Chart Type": chart_type
        })
    
    seen_columns = set()
    for datasource_name, caption in datasource_map.items():
        for column_name, column_caption in column_map.items():
            column_datatype = column_type_map.get(column_name, "Unknown")
            column_formula = column_formula_map.get(column_name, "No Formula")
            normalized_column_name = normalize_column_name(column_name)
            if normalized_column_name and normalized_column_name not in seen_columns:
                datasource_data.append({
                    "Datasource Caption": caption,
                    "Column Name": column_name,
                    "Column Caption": column_caption,
                    "Column Datatype": column_datatype,
                    "Formula": column_formula
                })
                seen_columns.add(normalized_column_name)
                if column_formula != "No Formula":
                    calculated_column_count += 1 

    worksheet_df = pd.DataFrame(worksheet_data)

    worksheet_df['Rows'] = worksheet_df['Rows'].str.replace(r'\bnone:', '', regex=True).str.strip()
    worksheet_df['Columns'] = worksheet_df['Columns'].str.replace(r'\bnone:', '', regex=True).str.strip()

    for column_name, column_caption in column_map.items():
        worksheet_df['Rows'] = worksheet_df['Rows'].str.replace(column_name, column_caption)
        worksheet_df['Columns'] = worksheet_df['Columns'].str.replace(column_name, column_caption)

    datasource_df = pd.DataFrame(datasource_data)

    # Create Summary DataFrame
    summary_data = {
        "Workbook Name": [workbook_name],
        "# of Dashboards": [len(dashboard_names)],
        "# of Datasources": [len(datasource_map)],
        '# of Worksheets' : [worksheet_count],
        "# of Calculated Columns": [calculated_column_count],
        "# of Dashboard Filters": [dashboard_filters_count]  
    }
    summary_df = pd.DataFrame(summary_data)

    return worksheet_df, datasource_df, summary_df

def main():
    st.title("Tableau Metadata Extractor")
    
    uploaded_files = st.file_uploader("Upload Tableau TWB files", type="twb", accept_multiple_files=True)
    
    if uploaded_files:
        all_worksheet_data = []
        all_datasource_data = []
        all_summary_data = []

        for uploaded_file in uploaded_files:
            worksheet_df, datasource_df, summary_df = parse_tableau_xml(uploaded_file)
            all_worksheet_data.append(worksheet_df)
            all_datasource_data.append(datasource_df)
            all_summary_data.append(summary_df)

        combined_worksheet_df = pd.concat(all_worksheet_data, ignore_index=True)
        combined_datasource_df = pd.concat(all_datasource_data, ignore_index=True)
        combined_summary_df = pd.concat(all_summary_data, ignore_index=True)

        st.subheader("Workbook Summary")
        st.dataframe(combined_summary_df)

        st.subheader("Frontend Analysis")
        st.dataframe(combined_worksheet_df)
        
        st.subheader("Backend Analysis")
        combined_datasource_df['Calculated Column'] = ['No' if i == 'No Formula' else 'Yes' for i in combined_datasource_df['Formula']]
        combined_datasource_df=process_dataframe(combined_datasource_df)
        st.dataframe(combined_datasource_df)
        
        summary_csv = combined_summary_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Summary Data as CSV", summary_csv, "tableau_summary_metadata.csv", "text/csv", key='download-summary-csv')

        worksheet_csv = combined_worksheet_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Worksheet Data as CSV", worksheet_csv, "tableau_worksheet_metadata.csv", "text/csv", key='download-worksheet-csv')
        
        datasource_csv = combined_datasource_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Datasource Data as CSV", datasource_csv, "tableau_datasource_metadata.csv", "text/csv", key='download-datasource-csv')

if __name__ == "__main__":
    main()

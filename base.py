import copy

import pandas as pd

import streamlit as st
import zipfile
import os
import io
import copy
from streamlit.runtime.uploaded_file_manager import UploadedFile

st.session_state['processed_files'] = set()
st.title("Is My Engine Fucked?")


def get_rpm_acceleration_data(base_path: str) -> pd.DataFrame:
    combined_df = None
    current_date = 'unknown'

    for i in os.listdir(base_path):
        if '.csv' in i and 'LAP' in i:
            df = pd.read_csv(os.path.join(*[base_path,i]))
            df['next_speed'] = df['Speed GPS'].shift(-1)

            df['acceleration'] = df['next_speed'] - df['Speed GPS']
            wanted_df = df[(df['acceleration'] > 0) & (df['RPM'] > 3500)][['RPM', 'acceleration', 'Speed GPS']]
            wanted_df['normalized_acc'] = wanted_df['acceleration'] * wanted_df['Speed GPS'] ** 2
            if combined_df is None:
                combined_df = wanted_df
            else:
                combined_df = pd.concat([combined_df, wanted_df])
        elif '.csv' in i and 'SN' in i:
            date_df = pd.read_csv(os.path.join(*[base_path,i]))
            current_date = date_df.columns[0]
            current_time = date_df.columns[1]

    combined_df['RPM_bin'] = pd.cut(combined_df['RPM'], bins=[3500, 4000, 4500, 5000, 5500, 6000, 6500])
    result = combined_df.groupby('RPM_bin')['normalized_acc'].quantile(0.8).reset_index()
    result['mid'] = result['RPM_bin'].apply(lambda x: int(x.mid))



    # fig, ax = plt.subplots(figsize=(10, 6))
    # ax.plot(result['RPM_bin'].apply(lambda x: x.mid), result['normalized_acc'], marker='o', linestyle='-', color='b')
    # ax.set_title(current_date + '|' + str(current_time))
    # ax.axis([3500, 6300, 1000000, 6000000])
    return result

st.info("this only works with alfano files, plz drop a known good engine run in the form of an alfano zip")

good_runs_ls = list()
good_runs = st.file_uploader(label="known good engine run(s)", accept_multiple_files=True)

if not os.path.exists('./extracted'):
    os.mkdir('./extracted')
for uploaded_file in good_runs:
    if type(uploaded_file) == UploadedFile:
        extract_dir = f'./extracted/{uploaded_file.file_id}'
        if not os.path.exists(extract_dir):
            os.mkdir(extract_dir)


        with zipfile.ZipFile(io.BytesIO(uploaded_file.read()), "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # iterate through all the files and grab the known good runs
        result = get_rpm_acceleration_data(extract_dir)
        st.title("your reference good engine run")
        st.line_chart(data=result,
                x='mid',
                y='normalized_acc',
                      x_label="rpm_midpoint",
                      y_label="normalized_acceleration",
                      color="#097969")

        good_runs_ls.append(result)
        st.session_state.processed_files.update(uploaded_file.file_id)

st.info("everything else goes here")

others = st.file_uploader(label="other runs", accept_multiple_files=True)
other_runs = dict()
for b in others:
    if type(b) == UploadedFile:

        extract_dir = f'./extracted/{b.file_id}'
        if not os.path.exists(extract_dir):
            os.mkdir(extract_dir)


        with zipfile.ZipFile(io.BytesIO(b.read()), "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        result = get_rpm_acceleration_data(extract_dir)

        # os.rmdir(extract_dir, )
        other_runs[b.name] =result

if other_runs:
    combined = None
    display_cols = list()
    st.title("Other Runs only")

    if len(other_runs) > 1:
        for key, run_df in other_runs.items():
            if type(combined) != pd.DataFrame:
                combined = run_df[['mid', 'normalized_acc']].rename(columns={'normalized_acc': key})

            else:
                combined = combined.merge(
                    run_df[['mid', 'normalized_acc']].rename(columns={'normalized_acc': key}),
                    on='mid',
                    how='outer',
                )
            display_cols.append(key)




        st.line_chart(data=combined,
                      x='mid',
                      y=list(other_runs.keys()),
                      x_label="rpm_midpoint",
                      y_label="normalized_acceleration")

    else:
        st.line_chart(data=other_runs[list(other_runs.keys())[0]],
                      x='mid',
                      y='normalized_acc',
                      x_label="rpm_midpoint",
                      y_label="normalized_acceleration")


    st.title("Other Runs with GOOD run")
    new = copy.deepcopy(combined)
    new_plot_cols = list(other_runs.keys())
    print('good runs',good_runs_ls)
    for index, g in enumerate(good_runs_ls):
        print("adding final_good run")
        run_name = f"good run: {index}"
        new = new.merge(
            g[['mid', 'normalized_acc']].rename(columns={'normalized_acc': run_name}),
            on='mid',
            how='outer',
        )
        new_plot_cols.append(run_name)

    print(new)
    st.line_chart(data=new,
                  x='mid',
                  y=new_plot_cols,
                  x_label="rpm_midpoint",
                  y_label="normalized_acceleration")



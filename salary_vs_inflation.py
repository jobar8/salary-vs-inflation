"""Streamlit app to calculate salaries in real terms."""

from typing import overload

import altair as alt
import pandas as pd
import streamlit as st
from numpy.typing import ArrayLike, NDArray

st.title('Salary vs Inflation')
st.markdown("""
    This tool shows the effect of inflation on your buying power.  
    First enter your salary for one or several years in the table below.
    Using the Customer Price Index (CPI), your salary in real terms ("Eroded Salary") is then calculated for
    subsequent years, showing how much money you are losing if your wages are not
    re-evaluated every year ("Target Salary").
    """)

with st.expander('Additional information'):
    st.markdown("""
    #### Origin of data

    The Consumer Price Index (CPI) data for the UK was downloaded from
    the [ONS](https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7bt/mm23) website. It covers
    the period from 1988 onwards.

    #### Calculations

    In order to convert the salary you had at a given year ($year1$) into the salary you should
    have had in $year2$ (with $year2 > year1$) if it had followed the inflation, the following formula has been used:
    """)
    st.latex(r"""Salary_{year2} = Salary_{year1} \times \frac{CPI_{year2}}{CPI_{year1}}""")
    st.markdown("""
    In the app below, $Salary_{year2}$ is called "target salary" and $year1$ is called "reference year".
    The reference year is by default the previous year entered in the table. So there could be several of them.
    It is assumed that each entry is an update to your salary that "resets" the effects of inflation.  
    Note that, in order to get what your "$year1$'s salary" is actually worth in "$year2$'s money" (what I call the
    "eroded salary"), then one can simply invert the ratio of CPIs.  
    Finallly, a unique reference year can also be used to study long-term trends. 
                """)


@st.cache_data
def load_cpi():
    return pd.read_csv('data/cpi_by_year.csv', index_col='year')


# Load CPI data and show in the sidebar
with st.sidebar:
    data_load_state = st.text('Loading CPI data...')
    cpi_year = load_cpi()
    data_load_state.text('Info: CPI data loaded')
    st.subheader('CPI Data (ONS)')
    st.dataframe(cpi_year, height=600)


@overload
def calculate_inflation(year1: int, year2: int) -> float: ...
@overload
def calculate_inflation(year1: ArrayLike, year2: ArrayLike) -> NDArray: ...
def calculate_inflation(year1, year2):
    """Calculate inflation between `year1` and `year2` as the ratio of CPIs."""
    return cpi_year.loc[year2].to_numpy() / cpi_year.loc[year1].to_numpy()


def calculate_adjusted_salaries(salaries_dict: dict[int, float], target_year: int | None = None) -> pd.DataFrame:
    """Transform salaries from a given year to a target year."""
    salaries = pd.Series(salaries_dict, name='Salary').rename_axis(index='year').sort_index().to_frame()
    all_salaries, _ = salaries.align(pd.DataFrame([[0]], index=pd.RangeIndex(salaries.index[0], 2025)), axis=0)
    all_salaries['reference'] = salaries.index.to_series().astype(int)
    all_salaries = all_salaries.ffill().bfill().rename_axis(index='year')

    if target_year is None:
        inflation = calculate_inflation(all_salaries['reference'], all_salaries.index).flatten()
    else:
        inflation = calculate_inflation(target_year, all_salaries.index).flatten()

    all_salaries['Eroded Salary'] = all_salaries['Salary'] / inflation
    all_salaries['Target Salary'] = all_salaries['Salary'] * inflation

    # This ensures better looking plots because of the date index
    all_salaries.index = pd.to_datetime(all_salaries.index, format='%Y')

    return all_salaries


# Input table
st.subheader('Your salary (per year)', divider=True)
st.caption('Edit the table below to enter your own data. Rows can be added or removed.')
salaries = {2002: 24000.0, 2014: 35000, 2022: 55000}
salaries = st.data_editor(salaries, num_rows='dynamic', column_config={'_index': 'Year', 'value': 'Salary'})

st.subheader('Effect of inflation on your salary', divider=True)
plot_container = st.empty()  # empty container to display widgets out of order

# Reference year slider
with st.container(border=True):
    min_year = min(list(salaries.keys()))
    if st.checkbox('Use a single reference year'):
        reference_year = st.slider('Reference Year', min_year, 2024, 2002)
        adjusted_salaries = calculate_adjusted_salaries(salaries, target_year=reference_year)  # type: ignore
    else:
        reference_year = st.slider('Reference Year', min_year, 2024, 2002, disabled=True)
        adjusted_salaries = calculate_adjusted_salaries(salaries, target_year=None)  # type: ignore

salary_types = ['Salary', 'Eroded Salary', 'Target Salary']
adjusted_salaries_longform = (
    adjusted_salaries[salary_types].reset_index().melt('year', var_name='Salary', value_name='Value')
)

chart1 = (
    alt.Chart(adjusted_salaries_longform)
    .mark_line(point=True)
    .encode(
        alt.X('year', type='temporal').axis(title=''),
        alt.Y('Value', type='quantitative').axis(title=''),
        color=alt.Color('Salary')
        .scale(domain=salary_types, range=['#468FE6', '#E64662', '#2CDC15'])
        .legend(orient='bottom', title=''),
    )
    .interactive()
)

plot_container.altair_chart(chart1, use_container_width=True)

with st.expander('Results as a table'):
    st.dataframe(adjusted_salaries, hide_index=False)

"""Streamlit app to calculate salaries in real terms."""

import streamlit as st
import pandas as pd

st.title("Salary vs Inflation")
st.markdown("""
    This tool shows the effect of inflation on your buying power.  
    First enter your salary for one or several years in the table below.
    Using the Customer Price Index (CPI), your salary in real terms is then calculated for subsequent years,
    showing how much money you are losing if your wages are not re-evaluated every year.
    """)

with st.expander("Additional information"):
    st.markdown("""
    #### Origin of data

    The Consumer Price Index (CPI) data for the UK was downloaded from
    the [ONS](https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7bt/mm23) website.

    #### Calculations

    In order to convert the salary you had at a given year ($year1$) into the salary you should
    have had in $year2$ if it had followed the inflation, the following formula has been used:
    """)
    st.latex(r"""Salary_{year2} = Salary_{year1} \times \frac{CPI_{year2}}{CPI_{year1}}""")
    st.markdown("""
    Note that, if $year2 < year1$, then you get what your "$year2$'s salary" is actually worth in
    "$year1$'s money". In the app below, $year2$ is called "target year" or "reference year".
                """)


@st.cache_data
def load_cpi():
    return pd.read_csv("data/cpi_by_year.csv", index_col="year")


# Load CPI data and show in the sidebar
with st.sidebar:
    data_load_state = st.text("Loading CPI data...")
    cpi_year = load_cpi()
    data_load_state.text("Info: CPI data loaded")
    st.subheader("CPI Data (ONS)")
    st.dataframe(cpi_year, height=600)


def calculate_inflation(year1: int, year2: int) -> float:
    """Calculate inflation between `year1` and `year2` as the ratio of CPIs."""
    return cpi_year.loc[year2].iloc[0] / cpi_year.loc[year1].iloc[0]  # type: ignore


def calculate_adjusted_salaries(salaries_dict: dict[int, float], target_year: int = 2000) -> pd.DataFrame:
    """Transform salaries from a given year to a target year."""
    salaries = pd.Series(salaries_dict, name="Salary").rename_axis(index="year").sort_index().to_frame()
    all_salaries, _ = salaries.align(pd.DataFrame([[0]], index=pd.RangeIndex(salaries.index[0], 2024)), axis=0)
    all_salaries = all_salaries.ffill().bfill().rename_axis(index="year")
    all_salaries["Adjusted Salary"] = all_salaries.apply(
        lambda x: x.Salary * calculate_inflation(int(x.name), target_year),
        axis=1,
    )
    # This ensures better looking plots because of the date index
    all_salaries.index = pd.to_datetime(all_salaries.index, format="%Y")

    return all_salaries


st.subheader("Your salary (per year)", divider=True)

salaries = {2002: 24000.0, 2017: 40000, 2022: 55000}
salaries = st.data_editor(salaries, num_rows="dynamic", column_config={"_index": "Year", "value": "Salary"})

st.subheader("Effect of inflation on your salary", divider=True)
plot_container = st.empty()

# Reference year slider
min_year = min(list(salaries.keys()))
reference_year = st.slider("Reference Year", min_year, 2024, 2002)
adjusted_salaries = calculate_adjusted_salaries(salaries, target_year=reference_year)  # type: ignore
plot_container.line_chart(adjusted_salaries, color=["#E64662", "#468FE6"])

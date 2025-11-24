import streamlit as st
from carga_inei import page_1
from visualizacion import page_2

# Inicializa el estado
if "step" not in st.session_state:
    st.session_state.step = 1  # 1 = carga, 2 = visualización

# Flujo guiado
if st.session_state.step == 1:
    page_1()
elif st.session_state.step == 2:
    page_2()    
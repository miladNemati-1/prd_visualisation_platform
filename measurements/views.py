from cmath import e, log
from django.shortcuts import render, redirect
from experiments.models import Experiment
import plotly.express as px
from measurements.tables import MonomerTable
from .forms import AddFileForm
from .models import Measurement, Data, Monomer, Experiment, cta
from django.contrib.auth.decorators import login_required
from plotly.offline import plot
import plotly.graph_objects as go
import datetime
import pandas
import plotly.graph_objects as go
import numpy as np
from sklearn.model_selection import train_test_split
from django.views.decorators.csrf import csrf_exempt
from scipy import stats
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.tree import DecisionTreeRegressor
import plotly.graph_objects as go
from sklearn.ensemble import AdaBoostRegressor


def get_all_rate_data():
    df_experiments_cta_join = get_all_cleaned_res_time_conversion_data()

    df_measurement_rate = add_experiment_rate_values_column(
        df_experiments_cta_join)

    df_measurement_rate = df_measurement_rate.set_index('rate_measurement_join_column').join(
        df_experiments_cta_join.set_index('rate_measurement_join_column'))

    df_measurement_rate.drop(
        ['res_time', 'result', 'id'], axis=1, inplace=True)
    df_measurement_rate = df_measurement_rate.drop_duplicates()
    df_measurement_rate.replace('', np.nan, inplace=True)
    df_measurement_rate.dropna(inplace=True)
    # df_measurement_rate.to_csv("/Users/miladnemati/Desktop/All_rate_data.csv")

    return df_measurement_rate


def get_all_cleaned_res_time_conversion_data():
    monomer_info_df = pandas.DataFrame(
        list(Monomer.objects.values()))

    cta_info_df = pandas.DataFrame(
        list(cta.objects.values()))

    experiment_df = pandas.DataFrame(
        list(Experiment.objects.values()))

    df_measurements = pandas.DataFrame(
        list(Measurement.objects.values()))

    df_data_measurements = pandas.DataFrame(
        list(Data.objects.values()))

    df_data_measurements['rate_measurement_join_column'] = df_data_measurements['measurement_id']

    df_measurements_measurement_rate_join = df_measurements.set_index('id').join(
        df_data_measurements.set_index('measurement_id'))

    df_experiments_measurement_rate_join = experiment_df.set_index('id').join(
        df_measurements_measurement_rate_join.set_index('experiment_id'))

    df_experiments_monomer_join = df_experiments_measurement_rate_join.set_index('monomer_id').join(
        monomer_info_df.set_index('id').add_prefix('monomer_'))
    df_experiments_cta_join = df_experiments_monomer_join.set_index('cta_id').join(
        cta_info_df.set_index('id').add_prefix('cta_'))

    # clean data using data jump removal method
    clean_timesweep_data(df_experiments_cta_join)
    df_experiments_cta_join.replace('', np.nan, inplace=True)
    df_experiments_cta_join.dropna(inplace=True)
    # df_experiments_cta_join.to_csv(
    #     "/Users/miladnemati/Desktop/df_experiments_cta_join.csv")

    return df_experiments_cta_join


def determine_rate_of_data_subset(data_subset):

    results_floats = [((log(1-float(x), e))).real
                      for x in data_subset['result']]
    res_time_floats = [float(x) for x in data_subset['res_time']]

    fit = stats.linregress(
        res_time_floats, results_floats)
    k = fit[0]
    if fit[2]**2 < 0.70:
        return np.nan

    return abs(k)


@csrf_exempt
def add_experiment_rate_values_column(df_measurements: pandas.DataFrame):

    measurement_id_rate_arr = []
    unique_data_set = set(
        list(df_measurements['rate_measurement_join_column']))
    for unique_measurement_id in unique_data_set:
        data_subset = pandas.DataFrame(
            df_measurements[df_measurements["rate_measurement_join_column"] == unique_measurement_id])
        measurement_id_rate_arr.append([unique_measurement_id,
                                        determine_rate_of_data_subset(data_subset)])

    rate_measurement_id_df = pandas.DataFrame(
        measurement_id_rate_arr, columns=("rate_measurement_join_column", "rate(s^-1)"))

    return rate_measurement_id_df


def remove_data_jumps(df_time_result):
    pointer = 0
    column = df_time_result['result']
    for i in range(len(column)-1):
        next_value = float(column.iloc[i+1])
        current_pointer_value = float(column.iloc[pointer])
        if current_pointer_value + (0.05*(current_pointer_value)) < next_value or (current_pointer_value) > next_value + (0.05*(next_value)):
            column.iloc[i+1] = ''
        elif next_value < 0:
            column.iloc[i+1] = ''
        else:
            pointer = i+1
    return df_time_result


def clean_timesweep_data(monomer_conversion: pandas.DataFrame):
    df = monomer_conversion[['monomer_name',
                             'cta_name', 'cta_concentration', 'temperature']]
    list_df = df.values.tolist()
    unique_rows = np.unique(list_df, axis=0)

    for row in unique_rows:
        data_slice = monomer_conversion.loc[(
            monomer_conversion['monomer_name'] == row[0]) & (monomer_conversion['cta_name']
                                                             == row[1]) & (monomer_conversion['cta_concentration'] == row[2]) & (monomer_conversion['temperature'] == row[3])]

        monomer_conversion.loc[(
            monomer_conversion['monomer_name'] == row[0]) & (monomer_conversion['cta_name']
                                                             == row[1]) & (monomer_conversion['cta_concentration'] == row[2]) & (monomer_conversion['temperature'] == row[3])] = remove_data_jumps(
            data_slice)

    return


def clean_data_frame(df):
    df.rename(columns={
        "monomer_name": "Monomer", 'cta_name': 'Chain Transfer Agent', 'res_time': 'Residence Time (min)', 'temperature': 'Temperature (°C)', "result": "Conversion %"}, inplace=True)
    df = modify_axis_all_visualisations(
        df, 'Residence Time (min)', "round((float(x)/60),3)")
    df = modify_axis_all_visualisations(
        df, 'Conversion %', "round(float(x),3)*100")

    return df


@ csrf_exempt
@ login_required
def all_visualisations(request):
    df = get_all_cleaned_res_time_conversion_data()
    print(list(df.columns.values))
    print("Error before clean data fram")
    df = clean_data_frame(df)
    print("Error after clean data fram")
    x = 'Monomer'
    y = 'Residence Time (min)'
    z = 'Conversion %'
    color = "Chain Transfer Agent"
    symbol = "cta_concentration"
    if request.method == "POST":
        x = request.POST.get("choose_x")
        y = request.POST.get("choose_y")
        z = request.POST.get("choose_z")
        x = request.POST.get("choose_x")
        color = request.POST.get("choose_colour")
        symbol = request.POST.get("choose_marker")
        x_input = request.POST.get("x-input")
        y_input = request.POST.get("y-input")
        z_input = request.POST.get("z-input")
        df = modify_axis_all_visualisations(df, x, x_input)
        df = modify_axis_all_visualisations(df, y, y_input)
        df = modify_axis_all_visualisations(df, z, z_input)

    three_d_graph = px.scatter_3d(df, x,
                                  y, z, color, symbol)
    three_d_graph = three_d_graph.to_html()

    column_names = ['cta_concentration', 'monomer_concentration', 'initiator_concentration',
                    'Temperature (°C)', 'Residence Time (min)', 'Conversion %', 'Chain Transfer Agent', 'Monomer']

    context = {

        'plot_3d_graph': three_d_graph,
        'column_names': column_names

    }
    return render(request, "measurements/all_visualisations.html", context)


def take_average_of_items_in_list(list):
    return sum(list)/len(list)


def create_descision_tree_from_df(df: pandas.DataFrame):
    df.dropna(inplace=True)
    X = df.iloc[:, :-1].values
    Y = df.iloc[:, -1].values.reshape(-1, 1)

    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=.2)
    regressor = AdaBoostRegressor(DecisionTreeRegressor())

    kinetics_model = regressor.fit(X_train, Y_train)

    Y_pred = kinetics_model.predict(X_test)
    Y_test = np.ndarray.flatten(Y_test)
    r_square = np.corrcoef(Y_test, Y_pred)[0, 1]

    error_tree_meansquared = np.sqrt(mean_squared_error(Y_test, Y_pred))

    return [kinetics_model, error_tree_meansquared]


def predict_from_model(fit, input):
    return fit.predict(input)


@ csrf_exempt
@ login_required
def monomer_models(request):

    df_experiments_cta_join = get_all_rate_data()

    predicted_k = "Predicted Rate"
    squared_error = "Mean Square Error"

    data_target = df_experiments_cta_join[(df_experiments_cta_join["monomer_name"] == 'BA') & (
        df_experiments_cta_join["cta_name"] == "Carbon Tetrabromide")]

    data_target = df_experiments_cta_join[[
        'temperature', 'cta_concentration', 'rate(s^-1)', ]]

    descision_tree = create_descision_tree_from_df(data_target)
    model = descision_tree[0]
    squared_error = descision_tree[1]

    if request.method == 'POST':
        temp = request.POST.get("r_temp")
        cx_cm = request.POST.get("r_cx_cm")

        prediction_input = [[temp, cx_cm]]
        predicted_k = predict_from_model(model, prediction_input)[0]

    context = {
        "predicted_k": predicted_k,
        "squared_error": squared_error

    }

    return render(request, "measurements/models_home.html", context)


def csv_to_db(file, pk):

    data = pandas.read_csv(file.file, encoding='UTF-8')

    data_conv = data[['conversion', 'tres']]
    data_conv['tres'] = data_conv.apply(
        lambda row: datetime.timedelta(minutes=row.tres).total_seconds(), axis=1)
    data_conv.rename(columns={'conversion': 'Conversion %',
                     'tres': 'res_time'}, inplace=True)
    data_conv['measurement_id'] = pk


@ login_required
def monomer_kinetics(request):
    monomers = MonomerTable(Monomer.objects.all())
    context = {
        'monomer': monomers,
    }

    return render(request, "measurements/show3Dplot.html", context)


@ login_required
def upload_file(request, pk):
    if request.method == 'POST':
        form = AddFileForm(request.POST, request.FILES, pk=pk)
        if form.is_valid():
            m = form.save()
            csv_to_db(m.file, m.pk)
        else:
            print(form.errors)

    return redirect('experiment_detail', pk=pk)


@ login_required
def delete_file(request, pk, path):
    if request.method == 'POST':
        file = Measurement.objects.get(pk=pk)
        file.delete()

    return redirect('experiment_detail', pk=path)


@ login_required
def view_graph(request, pk):

    df = pandas.DataFrame(
        list(Data.objects.filter(measurement_id=pk).values()))
    name = Measurement.objects.get(id=pk).experiment.name

    graph_conv = go.Scatter(x=df.res_time, y=df.result, mode='markers')

    # pad for centering and round to nearest 100
    max = df['res_time'].max() + df['res_time'].min()
    print(max)
    max = int(float(max))
    max -= max % -100
    print(max)

    layout_conv = {
        'title': name + ": conversion",
        'xaxis_title': 't_res (s)',
        'xaxis_range': [0, max],
        'yaxis_title': 'conversion',
        'height': 630,
        'width': 840,
        'paper_bgcolor': 'rgba(0,0,0,0)',
    }

    plot_conv = plot(
        {'data': graph_conv, 'layout': layout_conv}, output_type='div')

    context = {
        'plot_conv': plot_conv,
    }

    return render(request, "measurements/view_graph.html", context)


def get_CTA_reaction_data(request, name):
    finale_merged_data = get_all_cleaned_res_time_conversion_data()
    filtered_data_experiments = finale_merged_data.loc[finale_merged_data['monomer_name'] == name]

    return filtered_data_experiments


def get_axis(list_data):

    x = list(list_data['temperature'])
    y = list(list_data['res_time'])
    z = list(list_data['result'])
    CTA = list(list_data['cta_name'])
    cx_ratio = list(list_data['cta_concentration'])

    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    z = np.array(z, dtype=float)
    cx_ratio = np.array(cx_ratio, dtype=float)
    return x, y, z, cx_ratio, CTA


def modify_axis_all_visualisations(data, axis_label, axis_input):

    new_data = list(data[axis_label])

    try:
        for i in range(len(new_data)):

            new_formula = str(axis_input).replace(
                "x", str(new_data[i]))
            new_data[i] = eval(new_formula).real

        data[axis_label] = new_data
    except:
        print("Not a valid visualisation formula")
        pass

    return data


def get_axis_data(list_data):
    x, y, z, cx_ratio, CTA = get_axis(list_data)

    data = {
        "Temperature (°C)": x,
        "Residence Time (min)": y,
        "Conversion %": z,
        "Chain Transfer Agent": CTA,
        "CTA concentration (M)": cx_ratio,

    }
    return data


def plot_2d_kinetic_graph(name):
    all_data = get_all_rate_data()
    data_subset = all_data.loc[all_data['monomer_name'] == name]
    data_subset['Temperature (°C)'] = pandas.to_numeric(
        data_subset['temperature'])
    data_subset['Rate(1/s)'] = pandas.to_numeric(data_subset['rate(s^-1)'])

    scatter_plot = px.scatter(data_subset,
                              x='Temperature (°C)', y='Rate(1/s)', color='cta_name', symbol='cta_concentration', trendline='ols', trendline_scope='overall')
    scatter_plot.update_traces(marker=dict(size=12))
    results = px.get_trendline_results(scatter_plot)
    scatter_plot.update_layout(
        font=dict(
            size=20,
        ))
    results = results.iloc[0]["px_fit_results"].summary()
    plot_html_output = scatter_plot.to_html()

    return plot_html_output


def plot_3d_kinetic_graph(name):
    all_data = get_all_rate_data()
    data_subset = all_data.loc[all_data['monomer_name'] == name]
    data_subset['Temperature (°C)'] = pandas.to_numeric(
        data_subset['temperature'])
    data_subset['Rate(1/s)'] = pandas.to_numeric(data_subset['rate(s^-1)'])

    fig = px.scatter_3d(data_subset, x='Temperature (°C)',
                        y='Rate(1/s)', z='cta_concentration', color="cta_name")
    fig.update_traces(marker=dict(size=5),
                      selector=dict(mode='markers'))
    fig.update_layout(
        font=dict(
            size=10,
        )
    )
    return fig.to_html()


def plot_3d_graph(df):

    df = clean_data_frame(df)

    fig = px.scatter_3d(df, x='Temperature (°C)',
                        y='Residence Time (min)', z='Conversion %', color="Chain Transfer Agent", symbol="CTA concentration (M)")
    fig.update_traces(marker=dict(size=5),
                      selector=dict(mode='markers'))
    return fig.to_html()


@ csrf_exempt
@ login_required
def view_3d_graph(request, name):
    list_data = get_CTA_reaction_data(request, name)
    data = get_axis_data(list_data)
    df = pandas.DataFrame(data)

    axis = [
        "Temperature (°C)",
        "Residence Time (min)",
        "Conversion %"

    ]

    if request.method == 'POST':
        left_axis = request.POST.get("choose_x")
        left_input = request.POST.get("x-input")
        middle_axis = request.POST.get("choose_y")
        middle_input = request.POST.get("y-input")
        right_axis = request.POST.get("choose_z")
        right_input = request.POST.get("z-input")

        df = modify_axis_all_visualisations(df, left_axis, left_input)
        df = modify_axis_all_visualisations(df, middle_axis, middle_input)
        df = modify_axis_all_visualisations(df, right_axis, right_input)
    plot_3d = plot_3d_graph(df)
    context = {
        'plot_3d_graph': plot_3d,
        'axis': axis,
        'name': name

    }

    return render(request, 'measurements/3D_graph.html', context)


@ csrf_exempt
@ login_required
def view_3d_kinetic_graph(request, name):

    list_data = get_CTA_reaction_data(request, name)

    temperature, y, z, cx_ratio, CTA = get_axis(list_data)
    data = get_axis_data(list_data)

    df = pandas.DataFrame(data)
    k = "rate constant"
    CTA_list = set(CTA)
    temperature_list = set(temperature)

    reaction_orders = [
        "1st Order",
        "2nd Order",
        "3rd Order"
    ]
    cx_ratio = set(cx_ratio)

    if request.method == 'POST':
        CTA_chosen = request.POST.get("CTA")
        Temperature_chosen = request.POST.get("temperature")
        cx_ratio_chosen = request.POST.get("cta_concentration")

        df = df.loc[(df['temperature(C)'] == float(Temperature_chosen)) & (
            df['Chain Transfer Agent'] == CTA_chosen) & (
            df['cta_concentration'] == float(cx_ratio_chosen))]
        try:
            k = determine_rate_of_data_subset(df)
        except:
            print("not valid")
    two_d_graph = plot_2d_kinetic_graph(name)
    three_d_rate_graph = plot_3d_kinetic_graph(name)
    three_d_graph = plot_3d_graph(df)
    context = {
        'temperature_list': temperature_list,
        'CTA_list': CTA_list,
        'name': name,
        'reaction_orders': reaction_orders,
        'plot_3d_graph': three_d_graph,
        'plot_2d_graph': two_d_graph,
        'plot_3d_rate_graph': three_d_rate_graph,
        'cta_concentration': cx_ratio,
        'k': k
    }

    return render(request, 'measurements/kinetic_view.html', context)

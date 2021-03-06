import os
import pickle
import pandas as pd
import numpy as np
import scipy.stats as stats
import itertools
import plotly.graph_objects as go
from monte_carlo import monte_carlo_results
from simpleac import SimPleAC

analysis_plot_dir = "./analysis/"
folder_names = ["./data/control/", "./data/margin/", "./data/robust_performance/", "./data/robust_gamma/"]
conditions = ["Control", "Margin", "Gamma Slider", "Performance Slider"]


def determine_settings(condition, folder_name, point_end="_point.txt"):
    ids = sorted(os.listdir(folder_name))
    for subject in ids:
        subj_path = folder_name + subject
        subj_points = sorted([x for x in os.listdir(subj_path)
                         if not x.endswith(".txt")], key = int)
        for subj_point in subj_points:
            point_path = subj_path + "/" + subj_point
            if os.path.isfile(point_path + point_end):
                with open(point_path + point_end, "r") as f:
                    all_lines = f.readlines()
                if all_lines[0] == "unknown\n":
                    settings = []
                    with open(point_path, "rb") as f:
                        sol = pickle.load(f)
                    if condition == conditions[0]:
                        settings.append((sol("A").magnitude*sol("S").magnitude)**0.5)
                        settings.append(sol("S").magnitude)
                        settings.append(sol("V_{f_{avail}}").magnitude)
                        settings.append(sol("C_L").magnitude)
                        print(subj_point)
                        print(settings)
                        with open(point_path + point_end, "w") as f:
                            f.write(str(settings)+"\n")
                            for line in all_lines[1:]:
                                f.write(line)
                    elif condition == conditions[1]:
                        settings.append(sol("m_ww").magnitude)
                        settings.append(sol("m_tsfc").magnitude)
                        settings.append(sol("m_vmin").magnitude)
                        settings.append(sol("m_range").magnitude)
                        print(subj_point)
                        print(settings)
                        with open(point_path + point_end, "w") as f:
                            f.write(str(settings)+"\n")
                            for line in all_lines[1:]:
                                f.write(line)


def save_point(point_path, point_end="_point.txt", model_gen=SimPleAC, seed=246, settings="unknown"):
    with open(point_path, "rb") as f:
        sol = pickle.load(f)
        perf, fail = monte_carlo_results(model_gen(), sol=sol, quiet=True, seed=seed)
    with open(point_path + point_end, "w") as f:
        f.write(str(settings) + "\n")
        f.write(str(perf)+", "+str(fail))
    return perf, fail


def get_points(folder_name, point_end="_point.txt", model_gen=SimPleAC, seed=246):
    pointids = {}
    idpoints = {}
    pointnum = {}
    ids = sorted(os.listdir(folder_name))
    for subject in ids:
        idpoints[subject] = []
        subj_path = folder_name + subject
        subj_points = sorted([x for x in os.listdir(subj_path)
                         if not x.endswith(".txt")], key = int)
        for subj_point in subj_points:
            point_path = subj_path + "/" + subj_point
            if os.path.isfile(point_path + point_end):
                with open(point_path + point_end, "r") as f:
                    pf_line = f.readlines()[1]
                    perf, fail = [float(x) for x in pf_line.split(", ")]
            else:
                perf, fail = save_point(point_path, point_end=point_end, model_gen=model_gen, seed=seed)
            if (perf, fail) in pointids:
                if subject not in pointids[(perf, fail)]:
                    pointids[(perf, fail)].append(subject)
            else:
                pointids[(perf, fail)] = [subject]
            pointnum[(perf, fail, subject)] = subj_point
            idpoints[subject].append((perf,fail))
    return pointids, idpoints, pointnum


def corrected_points(folder_name, point_end="_point.txt", model_gen=SimPleAC, seed=246):
    pointids = {}
    idpoints = {}
    pointnum = {}
    skipped = {}
    ids = sorted(os.listdir(folder_name))
    for subject in ids:
        idpoints[subject] = []
        skipped[subject] = []
        subj_path = folder_name + subject
        subj_points = sorted([x for x in os.listdir(subj_path)
                         if not x.endswith(".txt")], key = int)
        min_subj_point = int(subj_points[0])
        for subj_point in subj_points:
            perf = None
            point_path = subj_path + "/" + subj_point
            if os.path.isfile(point_path + point_end):
                with open(point_path + point_end, "r") as f:
                    all_lines = f.readlines()
                    pf_line = all_lines[1]
                    _, fail = [float(x) for x in pf_line.split(", ")]
                    if len(all_lines) >= 3:
                        perf = "SKIP" if "SKIP" in all_lines[2] else float(all_lines[2])
            else:
                _, fail = save_point(point_path, point_end=point_end, model_gen=model_gen, seed=seed)
            if perf is None:
                with open(point_path, "rb") as f:
                    sol = pickle.load(f)
                    nominal = SimPleAC(substitutions={k: sol(k) for k in ["S", "A", "V_{f_{avail}}", "C_L"]})
                    try:
                        nomsol = nominal.localsolve(verbosity=0)
                        perf = nomsol("W_f").to("lbf").magnitude
                    except Exception:
                        perf = "SKIP"
                with open(point_path + point_end, "a") as f:
                    f.write("\n" + str(perf))
            if perf != "SKIP" and perf != "SKIP\n":
                if (perf, fail) in pointids:
                    if subject not in pointids[(perf, fail)]:
                        pointids[(perf, fail)].append(subject)
                else:
                    pointids[(perf, fail)] = [subject]
                pointnum[(perf, fail, subject)] = int(subj_point)-min_subj_point
                idpoints[subject].append((perf,fail))
            else:
                skipped[subject].append(int(subj_point)-min_subj_point)

    return pointids, idpoints, pointnum, skipped


def count_regions(idpoints):
    regions = {}
    numregions = {}
    for idnum in idpoints:
        regions[idnum] = 0
        in_green = 0
        in_yellow = 0
        in_blue = 0
        for point in idpoints[idnum]:
            perf, fail = point
            if (perf <= 1200 and fail <= 30):
                in_green += 1
            elif (perf <= 2000 and fail <= 10):
                in_yellow += 1
            elif (perf <= 1100):
                in_blue += 1
        if in_green>0:
            regions[idnum] +=1
        if in_yellow>0:
            regions[idnum] +=1
        if in_blue>0:
            regions[idnum] +=1
        numregions[idnum] = (in_green, in_yellow, in_blue)
    return regions, numregions


def pareto(pointids):
    pareto_points = {}
    for point in pointids:
        perf, fail = point
        if (perf < 900 or perf > 2000):
            continue
        im_pareto = True
        im_not_pareto = []
        same = None
        for pareto_point in pareto_points:
            if (pareto_point[0] == perf and pareto_point[1] == fail):
                pass
            if (pareto_point[0] <= perf and pareto_point[1] <= fail):
                im_pareto = False
                break
            elif (pareto_point[0] >= perf and pareto_point[1] >= fail):
                im_not_pareto.append(pareto_point)
        if im_pareto:
            pareto_points[point] = pointids[point]
            for not_pareto_point in im_not_pareto:
                pareto_points.pop(not_pareto_point)
    return pareto_points


def compare_pareto(pointids_condition):
    pareto_points = {}
    for condition in conditions:
        for point in pointids_condition[condition]:
            perf, fail = point
            if (perf < 900 or perf > 2000):
                continue
            im_pareto = True
            im_not_pareto = []
            same = None
            for pareto_point in pareto_points:
                if (pareto_point[0] == perf and pareto_point[1] == fail):
                    pass
                elif (pareto_point[0] <= perf and pareto_point[1] <= fail):
                    im_pareto = False
                    break
                elif (pareto_point[0] >= perf and pareto_point[1] >= fail):
                    im_not_pareto.append(pareto_point)
            if im_pareto:
                if point in pareto_points:
                    pareto_points[point].append((pointids_condition[condition][point], condition))
                pareto_points[point] = [(pointids_condition[condition][point], condition)]
                for not_pareto_point in im_not_pareto:
                    pareto_points.pop(not_pareto_point)
    return pareto_points


def plot_compare_pareto():
    pointids_condition = {}
    for folder_name, condition in zip(folder_names, conditions):
        pointids_condition[condition], _, _, _ = corrected_points(folder_name)
    pareto_points = compare_pareto(pointids_condition)
    points = pareto_points
    title = "Compared Pareto"
    colorfn = lambda x: conditions.index(x[1])
    cmax = 3
    x = {}
    y = {}
    for i in range(4):
        x[i], y[i] = list(zip(*[point for point in pareto_points if conditions[i] in list(zip(*pareto_points[point]))[1]]))
        print(conditions[i])
        print(len(x[i]))
    fig = go.Figure(
        data=[go.Scatter(
                x=x[0], 
                y=y[0], 
                marker=dict(
                    size=6,
                    opacity=1),
                mode="markers",
                name=conditions[0]), 
            go.Scatter(
                x=x[1], 
                y=y[1], 
                marker=dict(
                    size=6,
                    opacity=1),
                mode="markers",
                name=conditions[1]),
            go.Scatter(
                x=x[2], 
                y=y[2], 
                marker=dict(
                    size=6,
                    opacity=1),
                mode="markers",
                name=conditions[2]),
            go.Scatter(
                x=x[3], 
                y=y[3], 
                marker=dict(
                    size=6,
                    opacity=1),
                mode="markers",
                name=conditions[3]),
            ],
        layout_title_text=title)
    fig.update_layout(
        autosize=False,
        width=800,
        height=600,
        yaxis=go.layout.YAxis(
            title_text="Failure Rate",
            range=[0,100],
            tickmode='array',
            tickvals=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            ticktext=["0%", "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"]
        ),
        xaxis=go.layout.XAxis(
            title_text="Fuel Consumed (lbs)",
            range=[900,2000]
        )
    )
    fig.add_shape(
        go.layout.Shape(
            type="rect",
            layer="below",
            x0=1200,
            y0=0,
            x1=2000,
            y1=10,
            fillcolor="rgba(240,255,220,0.4)",
            line=dict(
                color="white",
                width=1,
            ),
    ))
    fig.add_shape(
        go.layout.Shape(
            type="rect",
            layer="below",
            x0=900,
            y0=30,
            x1=1100,
            y1=100,
            fillcolor="rgba(220,255,240,0.4)",
            line=dict(
                color="white",
                width=1,
            ),
    ))
    fig.add_shape(
        go.layout.Shape(
            type="rect",
            layer="below",
            x0=900,
            y0=0,
            x1=1200,
            y1=30,
            fillcolor="rgba(200,255,200,0.4)",
            line=dict(
                color="white",
                width=1,
            ),
    ))
    fig.update_shapes(dict(xref='x', yref='y'))
    fig.show()
    if not os.path.exists(analysis_plot_dir):
        os.mkdir(analysis_plot_dir)
    fig.write_image(analysis_plot_dir+title+".png")


def plot_points(points, title, colorfn=len, cmax=8):
    x, y = list(zip(*points.keys()))
    colors = [colorfn(x) for x in points.values()]
    fig = go.Figure(
        data=[go.Scatter(
            x=x,
            y=y,
            marker=dict(
                size=6,
                color=colors,
                cmin=0,
                cmax=cmax,
                opacity=0.6,
                colorbar=dict(
                    title="",
                    outlinewidth=0,
                    tickwidth=0,
                    tickcolor='white'),
                colorscale="magma"),
            mode="markers")],
        layout_title_text=title)
    fig.update_layout(
        autosize=False,
        width=800,
        height=600,
        yaxis=go.layout.YAxis(
            title_text="Failure Rate",
            range=[0,100],
            tickmode='array',
            tickvals=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            ticktext=["0%", "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"]
        ),
        xaxis=go.layout.XAxis(
            title_text="Fuel Consumed (lbs)",
            range=[900,2000]
        )
    )
    fig.add_shape(
        go.layout.Shape(
            type="rect",
            layer="below",
            x0=1200,
            y0=0,
            x1=2000,
            y1=10,
            fillcolor="rgba(240,255,220,0.4)",
            line=dict(
                color="white",
                width=1,
            ),
    ))
    fig.add_shape(
        go.layout.Shape(
            type="rect",
            layer="below",
            x0=900,
            y0=30,
            x1=1100,
            y1=100,
            fillcolor="rgba(220,255,240,0.4)",
            line=dict(
                color="white",
                width=1,
            ),
    ))
    fig.add_shape(
        go.layout.Shape(
            type="rect",
            layer="below",
            x0=900,
            y0=0,
            x1=1200,
            y1=30,
            fillcolor="rgba(200,255,200,0.4)",
            line=dict(
                color="white",
                width=1,
            ),
    ))
    fig.update_shapes(dict(xref='x', yref='y'))
    fig.show()
    if not os.path.exists(analysis_plot_dir):
        os.mkdir(analysis_plot_dir)
    fig.write_image(analysis_plot_dir+title+".png")


def heatmap_points(points, title):
    hmap = np.zeros((51, 112)) +.0001
    for perf, fail in points:
        i_col = min(max(int((perf-900)/10)+1, 0), 111)
        i_row = int(fail/2)
        hmap[i_row, i_col] += 1
    hmap = np.log(hmap)
    ticks = np.round(np.logspace(np.log10(5),np.log10(80),5))
    x = [0] + list(np.linspace(900, 2000, 111)) + [6000]
    y = list(np.linspace(0, 100, 51))
    fig = go.Figure(
        data=[go.Heatmap(
            x=x,
            y=y,
            z=hmap,
            type='heatmap',
            zmin=-1,
            zmax=np.log(80),
            colorbar=dict(
                tickvals=np.log(ticks),
                ticktext=ticks),
            colorscale="magma")],
        layout_title_text=title)
    fig.update_layout(
        autosize=False,
        width=800,
        height=600,
        yaxis=go.layout.YAxis(
            title_text="Failure Rate",
            range=[0,100],
            tickmode = 'array',
            tickvals = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            ticktext = ["0%", "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"]
        ),
        xaxis=go.layout.XAxis(
            title_text="Fuel Consumed (lbs)",
            range=[900,2000]
        )
    )
    fig.show()
    if not os.path.exists(analysis_plot_dir):
        os.mkdir(analysis_plot_dir)
    fig.write_image(analysis_plot_dir+title+".png")


def compensation(pareto_points, regions, idfile, outfile):
    pareto_money = 20
    base_money = 20
    per_region = 3
    all_3 = 1
    per_point = pareto_money/len(pareto_points)
    comp = {}
    for idnum in regions:
        comp[idnum] = base_money + regions[idnum] * per_region
        if regions[idnum] == 3:
            comp[idnum] += all_3
    for pareto_point in pareto_points:
        ids = pareto_points[pareto_point]
        point_divide = len(ids)
        for idnum in ids:
            comp[idnum] += per_point/point_divide
    output = []
    idf = pd.read_excel(idfile, index_col=2)
    for idnum in comp:
        int_id = int(idnum.split(" (ID ")[1][:-1])
        output.append([idf.loc[int_id, "Email"], round(comp[idnum],2)])
    odf = pd.DataFrame(data=output, columns=["Email", "Dollars"])
    with pd.ExcelWriter(outfile) as writer:
        odf.to_excel(writer)


#TODO still uses uncorrected perf; but also don't need anymore
def fragility(folder_name, title, model_gen=SimPleAC, seed=358):
    point_end = "_frag%i.txt" %seed
    pointids, _, pointnum = get_points(folder_name, model_gen=model_gen)
    fragpointids, _, _ = get_points(folder_name, point_end, model_gen, seed)
    pps = pareto(pointids)
    fragpps = {}
    for pp in pps:
        for subject in pps[pp]:
            subj_point = pointnum[(pp, subject)]
            point_path = folder_name + subject + "/" + subj_point
            with open(point_path + point_end, "r") as f:
                pf_line = f.readlines()[1]
                perf, fail = [float(x) for x in pf_line.split(", ")]
            if (perf, fail) in fragpps:
                if subject not in fragpps[(perf, fail)]:
                    fragpps[(perf, fail)].append(subject)
            else:
                fragpps[(perf, fail)] = [subject]
    
    plot_points(fragpointids, "All Fragility Points-" + title + " (seed %i)" %seed)
    plot_points(fragpps, "Pareto Fragility Points-" + title + " (seed %i)" %seed)
    heatmap_points(fragpointids, "Fragility Heatmap-" + title + " (seed %i)" %seed)


def summary_stat_t_test(stat_conds, stat_name="stat"):
    for condition in conditions:
        print(("%s %s" %(condition, stat_name)))
        print(list(stat_conds[condition]))
        print("Average: %f" %np.mean(stat_conds[condition]))
        print("StDev: %f" %np.std(stat_conds[condition]))
    print("T-Tests")
    for condition1, condition2 in itertools.combinations(conditions, 2):
        _, pval = stats.ttest_ind(stat_conds[condition1], stat_conds[condition2], equal_var=False, nan_policy='raise')
        print("%s, %s p-value: %f" %(condition1, condition2, pval))


def plot_summary_stat(stat_conds, stat_name="stat"):
    fig = go.Figure()
    maximum = 0
    for condition in stat_conds:
        fig.add_trace(go.Violin(y=stat_conds[condition],
                            name=condition,
                            points='all',
                            box_visible=True,
                            meanline_visible=True))
        this_max = max(stat_conds[condition])
        if this_max > maximum:
            maximum = this_max

    fig.update_layout(
        autosize=False,
        width=800,
        height=600,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=go.layout.XAxis(
            title_text="Condition",
        ),
        yaxis=go.layout.YAxis(
            title_text=stat_name,
            range=[0,maximum],
            ticks="outside",
            gridcolor='rgba(0,0,0,.1)'
        )
    )
    fig.show()
    if not os.path.exists(analysis_plot_dir):
        os.mkdir(analysis_plot_dir)
    fig.write_image(analysis_plot_dir+stat_name+".png")


def plot_delta_t(delta_t):
    all_delta_t = {}
    for condition in delta_t:
        fig = go.Figure()
        for idnum in delta_t[condition]:
            fig.add_trace(go.Scatter(
                y=delta_t[condition][idnum],
                name=idnum,
                marker=dict(
                   size=6,
                   opacity=0.6),
                mode="markers"))

        max_numpoints = max([len(delta_t[condition][idnum]) for idnum in delta_t[condition]])
        avg_delta_t = [np.mean([d_t[i] for d_t in delta_t[condition].values() if len(d_t)>i]) for i in range(max_numpoints)]
        fig.add_trace(go.Scatter(
            y=avg_delta_t,
            name=idnum))
        fig.update_layout(
            autosize=False,
            width=800,
            height=600,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=go.layout.XAxis(
                title_text="Number Point",
                range=[0,100]
            ),
            yaxis=go.layout.YAxis(
                title_text="Delta Time to Point",
                ticks="outside",
                gridcolor='rgba(0,0,0,.1)',
                range=[0,350]
            ),
            title=condition
        )
        fig.show()
        if not os.path.exists(analysis_plot_dir):
            os.mkdir(analysis_plot_dir)
        fig.write_image(analysis_plot_dir+condition+"_delta_t.png")
        all_delta_t[condition] = avg_delta_t

    fig = go.Figure()
    for condition in conditions:
        fig.add_trace(go.Scatter(
            y=all_delta_t[condition],
            name=condition))
    fig.update_layout(
        autosize=False,
        width=800,
        height=600,
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=go.layout.XAxis(
            title_text="Number Point",
            range=[0,100]
        ),
        yaxis=go.layout.YAxis(
            title_text="Delta Time to Point",
            ticks="outside",
            gridcolor='rgba(0,0,0,.1)',
            range=[0,100]
        ),
        title="All Conditions"
    )
    fig.show()


def all_analysis(folder_name, condition):
    #pointids, idpoints, _ = get_points(folder_name)
    pointids, idpoints, _, _ = corrected_points(folder_name)
    pps = pareto(pointids)
    regions, _ = count_regions(idpoints)
    plot_points(pointids, "All Points-" + condition)
    plot_points(pps, "Pareto Points-" + condition)
    heatmap_points(pointids, "Heatmap-" + condition)
    # compensation(pps, regions, "./Participant ID and Email (Responses).xlsx",
    #             analysis_plot_dir + condition + "_Money.xlsx")

    # fragility(folder_name, condition)
    # fragility(folder_name, condition, seed=839)


def summary_stats():
    numpoints = {condition: [] for condition in conditions}
    numgreen = {condition: [] for condition in conditions}
    numyellow = {condition: [] for condition in conditions}
    numblue = {condition: [] for condition in conditions}
    numout = {condition: [] for condition in conditions}
    norm_numgreen = {condition: [] for condition in conditions}
    norm_numyellow = {condition: [] for condition in conditions}
    norm_numblue = {condition: [] for condition in conditions}
    norm_numout = {condition: [] for condition in conditions}
    endtimes = {condition: [] for condition in conditions}
    timesgreen = {condition: [] for condition in conditions}
    timesyellow = {condition: [] for condition in conditions}
    timesblue = {condition: [] for condition in conditions}
    numpareto = {condition: [] for condition in conditions}
    norm_numpareto = {condition: [] for condition in conditions}
    avg_delta_t = {condition: [] for condition in conditions}
    delta_t = {condition: {} for condition in conditions}
    grid_cover = {condition: [] for condition in conditions}
    pointids_condition = {}
    for folder_name, condition in zip(folder_names, conditions):
        pointids_condition[condition], idpoints, pointnum, skipped = corrected_points(folder_name)
        # pointids_condition[condition], idpoints, pointnum = get_points(folder_name)
        numpoints[condition] = [len(idpoints[idnum]) for idnum in idpoints]
        _, numregions = count_regions(idpoints)
        pps = pareto(pointids_condition[condition])
        numgreen[condition], numyellow[condition], numblue[condition] = list(zip(*numregions.values()))
        numout[condition] = np.subtract(np.subtract(np.subtract(numpoints[condition], numgreen[condition]), numyellow[condition]), numblue[condition])
        norm_numgreen[condition] = np.divide(numgreen[condition], numpoints[condition])
        norm_numyellow[condition] = np.divide(numyellow[condition], numpoints[condition])
        norm_numblue[condition] = np.divide(numblue[condition], numpoints[condition])
        norm_numout[condition] = np.divide(numout[condition], numpoints[condition])
        numpareto[condition] = [len([pp for pp in pps if idnum in pps[pp]]) for idnum in idpoints]
        norm_numpareto[condition] = np.divide(numpareto[condition], sum(numpareto[condition]))
        times = {idnum: [] for idnum in idpoints}
        timegreen = {idnum: None for idnum in idpoints}
        timeyellow = {idnum: None for idnum in idpoints}
        timeblue = {idnum: None for idnum in idpoints}
        points = list(pointnum.keys())
        points.sort(key = lambda x: int(pointnum[x]))
        for point in points:
            times[point[2]].append(int(pointnum[point]))
            if (timegreen[point[2]] is None and (point[0] <= 1200 and point[1] <= 30)):
                timegreen[point[2]] = int(pointnum[point])
            elif (timeyellow[point[2]] is None and ((point[0] <= 2000 and point[0] > 1200) and point[1] <= 10)):
                timeyellow[point[2]] = int(pointnum[point])
            elif (timeblue[point[2]] is None and (point[0] <= 1100 and point[1] > 30)):
                timeblue[point[2]] = int(pointnum[point])
        timesgreen[condition] = [timegreen[idnum] - min(times[idnum]) for idnum in times if timegreen[idnum] is not None]
        timesyellow[condition] = [timeyellow[idnum] - min(times[idnum]) for idnum in times if timeyellow[idnum] is not None]
        timesblue[condition] = [timeblue[idnum] - min(times[idnum]) for idnum in times if timeblue[idnum] is not None]
        endtimes[condition] = [max(times[idnum]) - min(times[idnum]) for idnum in times]
        delta_t[condition] = {idnum: np.subtract(times[idnum][1:],times[idnum][:-1]) for idnum in times}
        avg_delta_t[condition] = [item for sublist in delta_t[condition].values() for item in sublist]
        for idnum in idpoints:
            hmap = np.zeros((11, 23))
            for perf, fail in idpoints[idnum]:
                i_col = min(max(int((perf-900)/50)+1, 0), 22)
                i_row = int(fail/10)
                hmap[i_row, i_col] += 1
            grid_cover[condition].append(np.count_nonzero(hmap[:, 1:22]))

    pareto_points = compare_pareto(pointids_condition)
    id_pp = {condition: {idnum: 0 for idnum in sorted(os.listdir(folder_name))} for condition,folder_name in zip(conditions, folder_names)}
    for pp in pareto_points:
        for idnums in pareto_points[pp]:
            for idnum in idnums[0]:
                id_pp[idnums[1]][idnum] += 1
    combined_pareto = {condition: list(id_pp[condition].values()) for condition in conditions}

    summary_stat_t_test(numpoints, "Number of Points")
    summary_stat_t_test(numgreen, "Number of Points in Green")
    summary_stat_t_test(numyellow, "Number of Points in Yellow")
    summary_stat_t_test(numblue, "Number of Points in Blue")
    summary_stat_t_test(endtimes, "End Times")
    summary_stat_t_test(norm_numgreen, "Normalized Number of Points in Green")
    summary_stat_t_test(norm_numyellow, "Normalized Number of Points in Yellow")
    summary_stat_t_test(norm_numblue, "Normalized Number of Points in Blue")
    summary_stat_t_test(numout, "Number of Points Outside")
    summary_stat_t_test(norm_numout, "Normalized Number of Points Outside")
    summary_stat_t_test(timesgreen, "Time to first Green Point")
    summary_stat_t_test(timesyellow, "Time to first Yellow Point")
    summary_stat_t_test(timesblue, "Time to first Blue Point")
    summary_stat_t_test(numpareto, "Number of Points on Pareto")
    summary_stat_t_test(norm_numpareto, "Percent of Points on Pareto")
    summary_stat_t_test(combined_pareto, "Number of Points on Combined Pareto")
    summary_stat_t_test(avg_delta_t, "Delta T")
    summary_stat_t_test(grid_cover, "Grid Points Covered")

    plot_summary_stat(numpoints, "Number of Points")
    plot_summary_stat(numgreen, "Number of Points in Green")
    plot_summary_stat(numyellow, "Number of Points in Yellow")
    plot_summary_stat(numblue, "Number of Points in Blue")
    plot_summary_stat(endtimes, "End Times")
    plot_summary_stat(norm_numgreen, "Normalized Number of Points in Green")
    plot_summary_stat(norm_numyellow, "Normalized Number of Points in Yellow")
    plot_summary_stat(norm_numblue, "Normalized Number of Points in Blue")
    plot_summary_stat(numout, "Number of Points Outside")
    plot_summary_stat(norm_numout, "Normalized Number of Points Outside")
    plot_summary_stat(timesgreen, "Time to first Green Point")
    plot_summary_stat(timesyellow, "Time to first Yellow Point")
    plot_summary_stat(timesblue, "Time to first Blue Point")
    plot_summary_stat(numpareto, "Number of Points on Pareto")
    plot_summary_stat(norm_numpareto, "Percent of Points on Pareto")
    plot_summary_stat(combined_pareto, "Number of Points on Combined Pareto")
    plot_summary_stat(avg_delta_t, "Delta T")
    plot_summary_stat(grid_cover, "Grid Points Covered")

    # plot_delta_t(delta_t)


if __name__ == "__main__":
    
    for folder_name, condition in zip(folder_names, conditions):
        all_analysis(folder_name, condition)

    summary_stats()


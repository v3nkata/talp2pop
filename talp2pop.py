#!/usr/bin/env python3

"""

Author  : Venkata Ayyalasomayajula
Email   : venkata.ayyalasomayajula@gmail.com

"""
import re
import argparse
import logging

def extract_value(filename, key):

    pattern_str = rf"{re.escape(key)}:\s*(\S+)"
    pattern = re.compile(pattern_str)

    with open(filename, 'r') as file:
        for line in file:
            match = pattern.search(line)
            if match:
                return match.group(1)
    return None

def cl_parser():

    parser = argparse.ArgumentParser(
        description = 'Calculate POP metrics from one or more TALP reports')
    parser.add_argument('talp_report',
                        nargs = '+',
                        type = str,
                        help = 'Absolute path to the TALP report')
    parser.add_argument('-s',
                        '--scaling',
                        choices = ['weak','strong'],
                        default = 'weak',
                        help = 'Type of scaling')
    return parser.parse_args()

def get_raw_metrics(filename):

    raw_metrics = dict()    
   
    raw_metrics['ranks'] = int(extract_value(filename, 'Number of MPI processes'))
    raw_metrics['nodes'] = int(extract_value(filename, 'Number of nodes'))
    raw_metrics['t_elapsed'] = float(extract_value(filename, 'Elapsed Time (ns)')) / 1e9    
    raw_metrics['t_useful'] = float(extract_value(filename, 'Useful Time (ns)')) / 1e9
    raw_metrics['t_mpi'] = float(extract_value(filename, 'MPI Time (ns)')) / 1e9

    # compute average useful time
    raw_metrics['t_avg_useful'] = raw_metrics['t_useful'] / raw_metrics['ranks']

    return raw_metrics

def get_efficiencies(filename):

    efficiencies = dict()
    
    # TALP computes POP metrics by default
    efficiencies['PE'] = float(extract_value(filename, 'MPI Parallel efficiency'))
    efficiencies['LB'] = float(extract_value(filename, 'MPI Load Balance'))
    efficiencies['CE'] = float(extract_value(filename, 'MPI Communication efficiency'))

    return efficiencies

def comp_scal(metrics, scaling):

    ref_metrics = metrics[0]
    for m in metrics:
        compScal = ref_metrics['t_avg_useful'] / m['t_avg_useful']
        if scaling == 'strong':
            compScal *= ref_metrics['ranks'] / m['ranks']
        m['CS'] = compScal
        
        #Compute Global Efficiency
        m['GE'] = m['PE']*compScal 
    return metrics

def display_table(metrics):
    metric_descriptions = {
        "nodes" :   "Number of nodes                ",
        "ranks" :   "Total number of MPI ranks      ",
        "GE"    :   "Global Efficiency              ",
        "PE"    :   "   MPI Parallel Efficiency     ",
        "LB"    :   "       MPI Load Balance        ",  
        "CE"    :   "       Communication Efficiency",
        "CS"    :   "   Computational Scaling       ",
    }
   
    num_cols = len(metrics)
    width_cols = 7
    vert_separator = " | "
    width_vertSep = len(vert_separator)
    horiz_separator = "-" * (len(metric_descriptions["GE"]) + (width_cols+width_vertSep)*num_cols + width_vertSep)

    keys_eff = ["GE", "PE", "LB", "CE", "CS"]

    draw_table = ""
    draw_table += horiz_separator + "\n"

    draw_table += metric_descriptions['nodes'] + vert_separator 
    for m in metrics:
        draw_table += f'{m["nodes"]:{width_cols}d}' + vert_separator
    draw_table += "\n"
    draw_table += horiz_separator + "\n"

    draw_table += metric_descriptions['ranks'] + vert_separator
    for m in metrics:
        draw_table += f'{m["ranks"]:{width_cols}d}' + vert_separator

    draw_table += "\n"
    draw_table += horiz_separator + "\n"

    for key in keys_eff:
        row_eff = metric_descriptions[key] + vert_separator
        for m in metrics:
            row_eff += f'{m[key]:{width_cols}.2f}' + vert_separator
        draw_table += row_eff + "\n"
    draw_table += horiz_separator + "\n"

    print(draw_table)

 
def main():

    args = cl_parser()
    
    all_effs = list()
    all_metrics = list()
    final_metrics = list()

    for report in args.talp_report:
        all_effs.append(get_efficiencies(report))
        all_metrics.append(get_raw_metrics(report))

    # combine all the metrics
    final_metrics = [{**d1, **d2} for d1, d2 in zip(all_metrics, all_effs)]
    
    # sort according to ranks
    final_metrics_sorted = sorted(final_metrics, key=lambda x:x["ranks"])

    # Compute computational scalability
    comp_scal(final_metrics_sorted, args.scaling)
    
    if args.scaling == "strong":
        logging.info("Performing strong scaling")
    else:
        logging.info("Performing weak scaling")

    # Generate the metrics table 
    display_table(final_metrics_sorted) 
   
if __name__ == '__main__':

    #Set default level   
    logging.basicConfig(level=logging.INFO)

    main()


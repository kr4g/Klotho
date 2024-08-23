from klotho.topos.graphs.fields import *
from klotho.topos.graphs.fields.algorithms import *
from klotho.skora.visualization.field_plots import *

f1 = load_field('/Users/ryanmillett/Klotho/examples/thesis/field_A_B_interaction.pkl')
print(f1)
path = find_navigation_path(f1, 2000, 616)
# print(path)
plot_field_heatmap(f1, path=path)
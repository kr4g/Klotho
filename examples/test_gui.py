import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use('TkAgg')  # Set the backend before importing pyplot
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import networkx as nx
from tkcode import CodeEditor  # pip install tkcode

from klotho.chronos.rhythm_trees.rt import RhythmTree
from klotho.skora.graphs import graph_tree, plot_graph

class RhythmTreeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Rhythm Tree Builder")
        self.root.configure(bg='#333333')
        
        # Configure main window
        self.root.geometry("1200x800")
        
        # Create main frame with dark background
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create left frame for visualization
        self.viz_frame = ttk.Frame(self.main_frame)
        self.viz_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create right frame for controls
        self.control_frame = ttk.Frame(self.main_frame, width=200)
        self.control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # Add controls
        ttk.Label(self.control_frame, text="Time Signature:").pack(pady=(0, 5))
        self.tempus_entry = ttk.Entry(self.control_frame)
        self.tempus_entry.pack(pady=(0, 10))
        self.tempus_entry.insert(0, "4/4")
        
        ttk.Label(self.control_frame, text="Subdivisions:").pack(pady=(0, 5))
        self.subdivisions_entry = CodeEditor(
            self.control_frame,
            width=30,
            height=3,
            language="python",
            background="black",
            foreground="white",
            insertbackground="white",
            font=("Consolas", 11),
            autofocus=True,
            blockcursor=True,
            insertofftime=0,
            padx=10,
            pady=5,
            undo=True
        )
        self.subdivisions_entry.pack(pady=(0, 10))
        
        # Add auto-bracket completion
        def handle_bracket(event):
            # Check if there's a selection
            if self.subdivisions_entry.tag_ranges("sel"):
                # There is a selection
                selection = self.subdivisions_entry.get("sel.first", "sel.last")
                self.subdivisions_entry.delete("sel.first", "sel.last")
                self.subdivisions_entry.insert("insert", f"({selection})")
            else:
                # No selection, just insert empty brackets
                self.subdivisions_entry.insert("insert", "()")
                self.subdivisions_entry.mark_set("insert", "insert-1c")
            return "break"  # Prevent default behavior

        # Bind the ( key to our handler
        self.subdivisions_entry.bind('(', handle_bracket)
        
        self.generate_btn = ttk.Button(self.control_frame, text="Generate Tree", 
                                     command=self.generate_tree)
        self.generate_btn.pack(pady=10)
        
        # Initialize the figure
        plt.style.use('dark_background')
        self.fig = plt.figure(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.viz_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # Initial plot setup
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#333333')
        self.fig.patch.set_facecolor('#333333')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def parse_subdivisions(self, s: str) -> tuple:
        """Convert a string like '(1 1 (1 (1 1)) 1)' into proper nested tuples"""
        def tokenize(s: str) -> list:
            s = s.replace('(', ' ( ').replace(')', ' ) ')
            return [x for x in s.split() if x.strip()]
        
        def parse_tokens(tokens: list) -> tuple:
            if not tokens:
                return tuple()
            
            result = []
            i = 0
            while i < len(tokens):
                token = tokens[i]
                if token == '(':
                    # Find matching closing parenthesis
                    count = 1
                    j = i + 1
                    while count > 0:
                        if tokens[j] == '(':
                            count += 1
                        elif tokens[j] == ')':
                            count -= 1
                        j += 1
                    # Recursively parse the subexpression
                    result.append(self.parse_tokens(tokens[i+1:j-1]))
                    i = j
                elif token == ')':
                    i += 1
                else:
                    result.append(int(token))
                    i += 1
            return tuple(result)
        
        # Remove outer parentheses if present
        s = s.strip()
        if s.startswith('(') and s.endswith(')'):
            s = s[1:-1]
        
        return self.parse_tokens(self.tokenize(s))

    def generate_tree(self):
        try:
            def tokenize(s: str) -> list:
                s = s.replace('(', ' ( ').replace(')', ' ) ')
                return [x for x in s.split() if x.strip()]
            
            def parse_tokens(tokens: list) -> tuple:
                if not tokens:
                    return tuple()
                
                result = []
                i = 0
                try:
                    while i < len(tokens):
                        token = tokens[i]
                        if token == '(':
                            # Find matching closing parenthesis
                            count = 1
                            j = i + 1
                            while count > 0 and j < len(tokens):
                                if tokens[j] == '(':
                                    count += 1
                                elif tokens[j] == ')':
                                    count -= 1
                                j += 1
                            if count > 0:  # Unmatched opening parenthesis
                                raise ValueError("Unmatched parenthesis in expression")
                            # Recursively parse the subexpression
                            result.append(parse_tokens(tokens[i+1:j-1]))
                            i = j
                        elif token == ')':
                            i += 1
                        else:
                            try:
                                result.append(int(token))
                            except ValueError:
                                raise ValueError(f"Invalid number: {token}")
                            i += 1
                except IndexError:
                    raise ValueError("Incomplete expression")
                
                return tuple(result)
            
            # Parse inputs
            tempus = self.tempus_entry.get()  # e.g. "4/4"
            
            # Parse subdivisions
            subdivs_str = self.subdivisions_entry.get("1.0", "end-1c").strip()
            if subdivs_str.startswith('(') and subdivs_str.endswith(')'):
                subdivs_str = subdivs_str[1:-1]
            subdivs = parse_tokens(tokenize(subdivs_str))
            
            # Create RhythmTree and graph
            rt = RhythmTree(meas=tempus, subdivisions=subdivs)
            G = graph_tree(rt.meas, subdivs)
            
            # Get root node and calculate positions
            root = [n for n, d in G.in_degree() if d == 0][0]
            pos = {}
            def hierarchy_pos(G, root, width=1.0, vert_gap=0.1, xcenter=0.5, pos=None, parent=None, parsed=None, depth=0):
                if pos is None:
                    pos = {root:(xcenter, 1)}
                    parsed = [root]
                else:
                    y = 1 - (depth * vert_gap)
                    pos[root] = (xcenter, y)
                children = list(G.neighbors(root))
                if not isinstance(G, nx.DiGraph) and parent is not None:
                    children.remove(parent)
                if len(children) != 0:
                    dx = width / len(children)
                    nextx = xcenter - width / 2 - dx / 2
                    for child in children:
                        nextx += dx
                        hierarchy_pos(G, child, width=dx, vert_gap=vert_gap, xcenter=nextx, pos=pos, parent=root, parsed=parsed, depth=depth+1)
                return pos
            
            pos = hierarchy_pos(G, root)
            labels = nx.get_node_attributes(G, 'label')
            
            # Draw on our existing canvas
            self.ax.set_facecolor('#333333')
            
            # Draw nodes and edges
            for node, (x, y) in pos.items():
                self.ax.text(x, y, labels[node], ha='center', va='center', zorder=5,
                        bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="black"))
            
            nx.draw_networkx_edges(G, pos, ax=self.ax, arrows=False, width=2.0, edge_color='white')
            
            # Configure axes
            self.ax.set_xticks([])
            self.ax.set_yticks([])
            self.ax.axis('off')
            
            # Update canvas
            self.canvas.draw()
            
        except ValueError as e:
            messagebox.showerror("Parsing Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate tree: {str(e)}")

def main():
    root = tk.Tk()
    app = RhythmTreeGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

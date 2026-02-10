# # # OLD
# # def notate(rt: RT):
# #     def _process(node=0, parent_dur=symbolic_unit(rt.meas) * rt.meas.numerator):
# #         children = list(rt.graph.successors(node))
# #         if children:
# #             level_sum = sum(abs(rt.graph.nodes[c]['label']) for c in children)
            
# #             p_sum = rt.graph.nodes[node]['label'] if node != 0 else rt.graph.nodes[node]['label'].numerator
# #             print(f"{level_sum} : {p_sum}")
# #             # n, m = get_group_subdivision((p_sum, (level_sum,)))
# #             # print(f"n: {n}, m: {m}")
            
# #             for child in children:
# #                 child_label = rt.graph.nodes[child]['label']
# #                 sym_dur = symbolic_duration(child_label, parent_dur, (level_sum,))
# #                 unit = symbolic_unit(sym_dur)
# #                 mult = sym_dur.numerator if unit == sym_dur else child_label
# #                 if rt.graph.out_degree(child) == 0:  # leaf node
# #                     hdb = head_dots_beams(unit * mult)
# #                     print(f"Node {child} -> {hdb}")
# #                 else:  # internal node
# #                     # next_dur = symbolic_unit(sym_dur) * child_label
# #                     next_dur = symbolic_unit(sym_dur) * mult
# #                     _process(child, next_dur)
# #     return _process()


# def notate_multiple_rts(rts: List[RT]) -> List[str]:
#     """Generate Lilypond notation for multiple RhythmTrees.
#     Returns a list of strings, each containing Lilypond code for a separate staff."""
    
#     def _process_node(rt: RT, node=0, parent_dur=None) -> str:
#         children = list(rt.graph.successors(node))
#         if not children:
#             return ""
        
#         level_sum = sum(abs(rt.graph.nodes[c]['label']) for c in children)
#         p_sum = rt.graph.nodes[node]['label'] if node != 0 else rt.graph.nodes[node]['label'].numerator
        
#         tuplet = create_tuplet((p_sum, (level_sum,)))
        
#         # Process all children
#         child_notes = []
#         for i, child in enumerate(children):
#             child_label = rt.graph.nodes[child]['label']
#             is_tied = isinstance(child_label, float)
            
#             # Convert float to int for duration calculation, but remember it's tied
#             value = int(child_label) if is_tied else child_label
            
#             sym_dur = symbolic_duration(value, parent_dur, (level_sum,))
#             unit = symbolic_unit(sym_dur)
            
#             # Ensure sym_dur is a Fraction or similar type
#             if isinstance(sym_dur, float):
#                 sym_dur = Fraction(sym_dur).limit_denominator()
            
#             mult = sym_dur.numerator if unit == sym_dur else value
#             note_duration = unit * Fraction(mult)
            
#             if rt.graph.out_degree(child) == 0:  # leaf node
#                 hdb = head_dots_beams(note_duration)
#                 note_type = hdb[0]
#                 dots = '.' * hdb[1]
#                 beams = hdb[2]
                
#                 base_duration = {
#                     'square': '\\longa',
#                     'whole': '1',
#                     'half': '2',
#                     'quarter': '4',
#                 }[note_type]
                
#                 if isinstance(base_duration, str) and base_duration.startswith('\\'): 
#                     actual_duration = base_duration
#                 else:
#                     duration_value = int(base_duration)
#                     if beams > 0:
#                         duration_value *= 2 ** beams
#                     actual_duration = str(int(duration_value))
                
#                 is_rest = value < 0
#                 note = f"r{actual_duration}{dots}" if is_rest else f"bd{actual_duration}{dots}"
                
#                 # If this note is a float, the previous note should be tied TO it
#                 if i > 0 and is_tied:
#                     child_notes[-1] += " ~"
                
#                 child_notes.append(note)
#             else:
#                 next_dur = symbolic_unit(sym_dur) * mult
#                 child_notes.append(_process_node(rt, child, next_dur))
        
#         result = ' '.join(child_notes)
        
#         if tuplet:
#             n, m = tuplet
#             result = f"\\tuplet {n}/{m} {{ {result} }}"
        
#         return result

#     lily_codes = []
#     for rt in rts:
#         parent_dur = symbolic_unit(rt.meas) * rt.meas.numerator
#         lily_code = f"\\time {rt.meas}\n"  # Just the time signature
#         lily_code += _process_node(rt, parent_dur=parent_dur)
#         lily_codes.append(lily_code)
    
#     return lily_codes

# def create_lily_file_multiple(rts: List[RT], filename: str = "my_rhythms") -> str:
#     """Create a complete Lilypond file from multiple RhythmTrees.
    
#     Args:
#         rts: List of RhythmTree instances
#         filename: Output filename (without extension)
    
#     Returns:
#         Complete Lilypond code as string
#     """
#     lily_codes = notate_multiple_rts(rts)
    
#     lily_code = f'''\\version "2.24.0"
#     \\header {{
#         title = "Multiple Rhythm Trees"
#         tagline = ##f
#     }}
    
#     \\score {{
#         \\new StaffGroup <<
#             \\override Score.SpacingSpanner.strict-note-spacing = ##t
#             \\set Score.proportionalNotationDuration = #(ly:make-moment 1/8)
#     '''
    
#     for i, code in enumerate(lily_codes):
#         lily_code += f'''
#         \\new DrumStaff \\with {{
#             \\override StaffSymbol.line-count = #1
#             drumStyleTable = #drums-style
#             \\override Stem.direction = #up
#         }} {{
#             \\override Score.TupletNumber.text = #(lambda (grob) (tuplet-number::calc-fraction-text grob))
#             \\drummode {{
#                 {code}
#             }}
#         }}
#         '''
    
#     lily_code += '''
#         >>
#         \\layout { }
#     }
#     '''
    
#     # Write to file
#     with open(f"{filename}.ly", "w") as f:
#         f.write(lily_code)
    
#     return lily_code


# def notate_rt_with_abjad(rt: RT) -> abjad.Score:
#     """Generate an Abjad Score from a RhythmTree."""
    
#     def _process_node(node=0, parent_dur=symbolic_unit(rt.meas) * rt.meas.numerator) -> abjad.Container:
#         children = list(rt.graph.successors(node))
#         if not children:
#             return abjad.Container()
        
#         level_sum = sum(abs(rt.graph.nodes[c]['label']) for c in children)
#         p_sum = rt.graph.nodes[node]['label'] if node != 0 else rt.graph.nodes[node]['label'].numerator
        
#         tuplet = create_tuplet((p_sum, (level_sum,)))
        
#         # Process all children
#         components = []
#         for i, child in enumerate(children):
#             child_label = rt.graph.nodes[child]['label']
#             is_tied = isinstance(child_label, float)
            
#             # Convert float to int for duration calculation, but remember it's tied
#             value = int(child_label) if is_tied else child_label
#             # value = int(child_label)
            
#             sym_dur = symbolic_duration(value, parent_dur, (level_sum,))
#             unit = symbolic_unit(sym_dur)
#             mult = sym_dur.numerator if unit == sym_dur else value
            
#             if rt.graph.out_degree(child) == 0:  # leaf node
#                 hdb = head_dots_beams(unit * Fraction(mult))
#                 note_type = hdb[0]
#                 dots = hdb[1]
#                 beams = hdb[2]
                
#                 duration = abjad.Duration(1, int(unit.denominator))
#                 if value > 0:
#                     note = abjad.Note("c'", duration)
#                 else:
#                     note = abjad.Rest(duration)
                
#                 if is_tied:
#                     abjad.attach(abjad.Tie(), note)
                
#                 components.append(note)
#             else:
#                 next_dur = symbolic_unit(sym_dur) * mult
#                 child_container = _process_node(child, next_dur)
#                 components.append(child_container)
        
#         if tuplet:
#             n, m = tuplet
#             # Ensure the tuplet ratio is a pair of integers
#             tuplet_container = abjad.Tuplet((n, m), components)
#             return tuplet_container
        
#         return abjad.Container(components)

#     score = abjad.Score()
#     staff = abjad.Staff()
#     staff.append(_process_node())
#     score.append(staff)
    
#     return score

# def create_lily_file_with_abjad(rt: RT, filename: str = "rhythm") -> str:
#     """Create a complete Lilypond file from a RhythmTree using Abjad."""
    
#     score = notate_rt_with_abjad(rt)
    
#     # Create a LilyPondFile directly
#     lilypond_file = abjad.LilyPondFile(items=[score])
    
#     # Persist the file to disk
#     abjad.persist.as_ly(lilypond_file, filename + ".ly")
    
#     return abjad.lilypond(lilypond_file)

# def notate_multiple_rts_with_abjad(rts: List[RT]) -> abjad.Score:
#     """Generate an Abjad Score with multiple staves from a list of RhythmTrees."""
#     score = abjad.Score()
    
#     for rt in rts:
#         # Reuse the existing _process_node logic by calling notate_rt_with_abjad
#         # and extracting just the staff from its score
#         single_score = notate_rt_with_abjad(rt)
#         staff = single_score[0]  # Get the first (and only) staff
#         score.append(staff)
    
#     return score

# def create_lily_file_multiple_with_abjad(rts: List[RT], filename: str = "rhythms") -> str:
#     """Create a complete Lilypond file from multiple RhythmTrees using Abjad."""
#     score = notate_multiple_rts_with_abjad(rts)
    
#     # Create a LilyPondFile directly
#     lilypond_file = abjad.LilyPondFile(items=[score])
    
#     # Persist the file to disk
#     abjad.persist.as_ly(lilypond_file, filename + ".ly")
    
#     return abjad.lilypond(lilypond_file)

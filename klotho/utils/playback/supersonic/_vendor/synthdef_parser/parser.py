"""SynthDef file parser implementation."""
import struct
import json
from typing import Tuple, Dict, List

CALCULATION_RATES = {
    0: 'scalar',
    1: 'control',
    2: 'audio',
    3: 'demand'
}

BUFFER_UGENS = {
    'PlayBuf', 'RecordBuf', 'BufRd', 'BufWr',
    'BufDelayN', 'BufCombN', 'BufAlloc', 'BufFrames'
}


def pstring(data: bytes) -> Tuple[str, bytes]:
    """Parse a Pascal-style string from binary data.

    Args:
        data: Binary data containing the string

    Returns:
        Tuple of (decoded string, remaining data)
    """
    string = struct.Struct(f'{data[0]}s').unpack(data[1:data[0] + 1])
    return (string[0].decode('utf-8'), data[data[0] + 1:])


def parse_header(data: bytes) -> Tuple[Dict, bytes]:
    """Parse the SynthDef file header.

    Args:
        data: Binary data starting with header

    Returns:
        Tuple of (header dictionary, remaining data)
    """
    header_struct_fmt = '> 4s I x B'
    header_struct = struct.Struct(header_struct_fmt)
    header_data = data[:struct.calcsize(header_struct_fmt)]
    data = data[struct.calcsize(header_struct_fmt):]

    header_raw = header_struct.unpack(header_data)
    header = {
        "file_type": header_raw[0].decode('utf-8'),
        "version": header_raw[1],
        "synths": header_raw[2]
    }

    if header["file_type"] != "SCgf":
        raise ValueError("Not a valid SynthDef file")

    if header["version"] != 2:
        raise ValueError(f"Unsupported version: {header['version']}")

    return (header, data)


def parse_constants(data: bytes) -> Tuple[List[float], bytes]:
    """Parse the constants section of a SynthDef.

    Args:
        data: Binary data starting with constants section

    Returns:
        Tuple of (constants list, remaining data)
    """
    number_constants = struct.Struct('>I').unpack(data[:4])
    data = data[4:]

    constants_fmt = f'> {number_constants[0]}f'
    constants_struct = struct.Struct(constants_fmt)

    constants = list(constants_struct.unpack(
        data[:struct.calcsize(constants_fmt)]))
    data = data[struct.calcsize(constants_fmt):]

    return (constants, data)


def parse_parameters(data: bytes) -> Tuple[List[float], bytes]:
    """Parse the parameters section of a SynthDef.

    Args:
        data: Binary data starting with parameters section

    Returns:
        Tuple of (parameters list, remaining data)
    """
    number_parameters = struct.Struct('>I').unpack(data[:4])
    data = data[4:]

    parameters_fmt = f'> {number_parameters[0]}f'
    parameters_struct = struct.Struct(parameters_fmt)

    parameters = list(parameters_struct.unpack(
        data[:struct.calcsize(parameters_fmt)]))
    data = data[struct.calcsize(parameters_fmt):]

    return (parameters, data)


def parse_named_parameters(
    data: bytes,
    parameters: List[float]
) -> Tuple[Dict[str, float], bytes]:
    """Parse the named parameters section of a SynthDef.

    Args:
        data: Binary data starting with named parameters section
        parameters: List of parameter values

    Returns:
        Tuple of (named parameters dict, remaining data)
    """
    number_nparameters = struct.Struct('>I').unpack(data[:4])
    data = data[4:]

    nparameters = {}
    for _ in range(number_nparameters[0]):
        pname, data = pstring(data)
        pindex = struct.Struct('>I').unpack(data[:4])[0]
        data = data[4:]
        nparameters[pname] = parameters[pindex]

    return (nparameters, data)


def parse_ugens(
    data: bytes,
    constants: List[float]
) -> Tuple[List[Dict], bytes]:
    """Parse the UGen definitions section of a SynthDef.

    Args:
        data: Binary data starting with UGen definitions
        constants: List of constant values

    Returns:
        Tuple of (UGen definitions list, remaining data)
    """
    number_ugens = struct.Struct('>I').unpack(data[:4])
    data = data[4:]

    ugens = []

    for _ in range(number_ugens[0]):
        uname, data = pstring(data)
        calc_rate = data[0]

        data = data[1:]

        number_inputs = struct.Struct('>I').unpack(data[:4])[0]
        data = data[4:]

        number_outputs = struct.Struct('>I').unpack(data[:4])[0]
        data = data[4:]

        special_index = struct.Struct('>H').unpack(data[:2])[0]
        data = data[2:]

        inputs = []
        for _ in range(number_inputs):
            ugen_index = struct.Struct('>i').unpack(data[:4])[0]
            data = data[4:]

            if ugen_index == -1:
                constant_index = struct.Struct('>I').unpack(data[:4])[0]
                data = data[4:]
                inputs.append({'constant': constants[constant_index]})
            else:
                output_index = struct.Struct('>I').unpack(data[:4])[0]
                data = data[4:]
                if output_index == 0xFFFFFFFF:  # Packed inputs!
                    num_packed = struct.Struct('>I').unpack(data[:4])[0]
                    data = data[4:]
                    inputs.append({
                        'packed': {
                            'ugen_index': ugen_index,
                            'num_inputs': num_packed
                        }
                    })
                else:  # Regular UGen input
                    inputs.append({'output': [ugen_index, output_index]})

        outputs = []
        for _ in range(number_outputs):
            outputs.append(data[0])
            data = data[1:]

        ugen_dict = {
            'name': uname,
            'inputs': inputs,
            'outputs': outputs,
            'special_index': special_index,
            'calculation_rate': CALCULATION_RATES.get(calc_rate, f'unknown({calc_rate})')
        }

        if uname in BUFFER_UGENS:
            ugen_dict['buffer'] = special_index
            ugen_dict['type'] = 'buffer_ugen'
        else:
            ugen_dict['special_index'] = special_index
            ugen_dict['type'] = 'regular_ugen'

        ugens.append(ugen_dict)

    return (ugens, data)


def parse_variants(
    data: bytes,
    parameters: List[float],
) -> Tuple[Dict, bytes]:
    """Parse the variant definitions section of a SynthDef.

    Args:
        data: Binary data starting with variants section
        parameters: List of parameter values
        named_parameters: Dict of named parameter values

    Returns:
        Tuple of (variants dict, remaining data)
    """
    num_variants = struct.Struct('>H').unpack(data[:2])[0]
    data = data[2:]

    variants = {}
    for _ in range(num_variants):
        vname, data = pstring(data)

        vparams_fmt = f'>{len(parameters)}f'
        vparams_struct = struct.Struct(vparams_fmt)

        params = vparams_struct.unpack(data[:struct.calcsize(vparams_fmt)])
        data = data[struct.calcsize(vparams_fmt):]

        variants[vname] = params

    return (variants, data)


def parse_synth(data: bytes) -> Tuple[Dict, bytes]:
    """Parse a single SynthDef from binary data.

    Args:
        data: Binary data starting with SynthDef

    Returns:
        Tuple of (SynthDef dictionary, remaining data)
    """
    name, data = pstring(data)
    constants, data = parse_constants(data)
    parameters, data = parse_parameters(data)
    named_parameters, data = parse_named_parameters(data, parameters)
    ugens, data = parse_ugens(data, constants)
    variants, data = parse_variants(data, parameters)

    return ({
        'name': name,
        'constants': constants,
        'parameters': parameters,
        'named_parameters': named_parameters,
        'ugens': ugens,
        'variants': variants
    }, data)


def parse_synthdef(data: bytes) -> Dict:
    """Parse SynthDef binary data into a dictionary structure.

    Args:
        data: Complete SynthDef binary data

    Returns:
        Dictionary containing parsed SynthDef structure
    """
    header, data = parse_header(data)
    synths = {}

    for _ in range(header['synths']):
        synth, data = parse_synth(data)
        synths[synth['name']] = synth

    header['synths'] = synths
    return header


def parse_synthdef_file(file_path: str) -> Dict:
    """Parse a SynthDef file from disk.

    Args:
        file_path: Path to .scsyndef file

    Returns:
        Dictionary containing parsed SynthDef structure
    """
    with open(file_path, 'rb') as f:
        return parse_synthdef(f.read())


if __name__ == '__main__':
    import sys
    print(json.dumps(parse_synthdef_file(sys.argv[1]), indent=2))

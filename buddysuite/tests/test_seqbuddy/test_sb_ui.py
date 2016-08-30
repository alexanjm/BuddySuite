#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# NOTE: BioPython 16.6+ required.

"""
This program is free software in the public domain as stipulated by the Copyright Law
of the United States of America, chapter 1, subsection 105. You may modify it and/or redistribute it
without restriction.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

name: tests.py
version: 1.1
author: Stephen R. Bond
email: steve.bond@nih.gov
institute: Computational and Statistical Genomics Branch, Division of Intramural Research,
           National Human Genome Research Institute, National Institutes of Health
           Bethesda, MD
repository: https://github.com/biologyguy/BuddySuite
© license: None, this work is public domain

Description: Collection of PyTest unit tests for the AlignBuddy.py program
"""

import pytest
import os
import argparse
from copy import deepcopy
from unittest import mock
from Bio.Alphabet import IUPAC
import io
import urllib.error

from ... import SeqBuddy as Sb
from ... import buddy_resources as br

TEMP_DIR = br.TempDir()
VERSION = Sb.VERSION


def fmt(prog):
    return br.CustomHelpFormatter(prog)

parser = argparse.ArgumentParser(prog="SeqBuddy", formatter_class=fmt, add_help=False, usage=argparse.SUPPRESS,
                                 description='''\
\033[1mSeqBuddy\033[m
  See your sequence files. Be your sequence files.

033[1mUsage examples\033[m:
  SeqBuddy.py "/path/to/seq_file" -<cmd>
  SeqBuddy.py "/path/to/seq_file" -<cmd> | SeqBuddy.py -<cmd>
  SeqBuddy.py "ATGATGCTAGTC" -f "raw" -<cmd>
''')

br.flags(parser, ("sequence", "Supply file path(s) or raw sequence. If piping sequences "
                              "into SeqBuddy this argument can be left blank."),
         br.sb_flags, br.sb_modifiers, VERSION)

# This is to allow py.test to work with its own flags
in_args = parser.parse_args([])


# ##################### '-ano', '--annotate' ###################### ##
def test_annotate_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.annotate = ["misc_feature", "1-100,200-250", "+"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), skip_exit=True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "d22c44cf1a53624b58a86b0fb98c33a6"

    test_in_args = deepcopy(in_args)
    test_in_args.annotate = ["misc_feature", "1-100,200-250", "foo=bar", "hello=world", "-", "α4"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), skip_exit=True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "8c56cb3d6950ea43ce25f0c402355834"

    test_in_args = deepcopy(in_args)
    test_in_args.annotate = ["unknown_feature_that_is_t0o_long", "1-100,200-250", "foo=bar", "hello=world", "-", "α4"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), skip_exit=True)
    out, err = capsys.readouterr()
    assert "Warning: The provided annotation type is not part of the GenBank format standard" in err
    assert "Warning: Feature type is longer than 16 characters" in err


# ######################  '-asl', '--ave_seq_length' ###################### #
def test_ave_seq_length_ui(capsys, sb_resources):
    test_in_args = deepcopy(in_args)
    test_in_args.ave_seq_length = [False]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("p f"), True)
    out, err = capsys.readouterr()
    assert out == '428.38\n'

    test_in_args.ave_seq_length = ['clean']
    Sb.command_line_ui(test_in_args, sb_resources.get_one("p f"), True)
    out, err = capsys.readouterr()
    assert out == '427.38\n'


# ######################  '-btr', '--back_translate' ###################### #
def test_back_translate_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.back_translate = [False]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), True)
    out, err = capsys.readouterr()
    assert "Panxα4" in out

    test_in_args = deepcopy(in_args)
    test_in_args.back_translate = [["human", "o"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('p g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "b6bcb4e5104cb202db0ec4c9fc2eaed2"

    with pytest.raises(TypeError)as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), pass_through=True)
    assert "The input sequence needs to be protein, not nucleotide" in str(err)


# ######################  '-bl2s', '--bl2seq' ###################### #
def test_bl2s_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.bl2seq = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) in ['339377aee781fb9d01456f04553e3923', 'ae5cc2703ece3012956db53993101967']

    Sb.command_line_ui(test_in_args, Sb.SeqBuddy(sb_odd_resources["duplicate"]), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) in ['d24495bd87371cd0720084b5d723a4fc', '920e77d01f0d9f671a517c3db06a74c4',
                                           '7e7b3d875aac282dd9495876d2c877d4']
    assert err == "Warning: There are records with duplicate ids which will be renamed.\n"

    # noinspection PyUnresolvedReferences
    with mock.patch.dict(os.environ, {"PATH": ""}):
        with mock.patch('builtins.input', return_value="n"):
            with pytest.raises(RuntimeError) as err:
                Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), pass_through=True)
            assert "not present in $PATH or working directory" in str(err)


# ######################  '-bl', '--blast' ###################### #
def test_blast_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.blast = [[sb_odd_resources["blastn"]]]
    tester = sb_resources.get_one('d f')
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) in ["a56ec76a64b25b7ca8587c7aa8554412"]

    Sb.command_line_ui(test_in_args, Sb.SeqBuddy(sb_odd_resources["blank"]), True)
    out, err = capsys.readouterr()
    assert out == "No significant matches found\n"

    with pytest.raises(RuntimeError) as err:
        test_in_args.blast = "./foo.bar"
        Sb.command_line_ui(test_in_args, tester, pass_through=True)
    assert "The .nhr file of your blast database was not found. " \
           "Ensure the -parse_seqids flag was used with makeblastdb." in str(err)


# ######################  '-cs', '--clean_seq' ###################### #
def test_clean_seq_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.clean_seq = [[None]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "dc53f3be7a7c24425dddeea26ea0ebb5"

    test_in_args.clean_seq = [["strict"]]
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy(sb_odd_resources["ambiguous_dna"]), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "1912fadb5ec52a38ec707c58085b86ad"

    test_in_args.clean_seq = [["strict", "X"]]
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy(sb_odd_resources["ambiguous_dna"]), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "4c10ba4474d7484652cb633f03db1be1"


# ######################  '-cmp', '--complement' ###################### #
def test_complement_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.complement = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "e4a358ca57aca0bbd220dc6c04c88795"

    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), pass_through=True)
    assert "Nucleic acid sequence required, not protein." in str(err)


# ######################  'cts', '--concat_seqs' ###################### #
def test_concat_seqs_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.concat_seqs = [True]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "7421c27be7b41aeedea73ff41869ac47"

    test_in_args.concat_seqs = ["clean"]
    test_in_args.out_format = "embl"
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d n'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "15b9c79dea034cef74e3a622bd357705"


# ######################  '-cc', '--count_codons' ###################### #
def test_count_codons_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.count_codons = ["foo"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "5661f0ce92bb6cfba4519a61e0a838ed"

    test_in_args.count_codons = ["conc"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "3e76bd510de4a61efb17ffc186ef9e68"

    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one("p g"), pass_through=True)
    assert "Nucleic acid sequence required, not protein" in str(err)


# ######################  '-cr', '--count_residues' ###################### #
def test_count_residues_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.count_residues = ["foo"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "c9bc54835fb54232d4d346d04344bf8b"

    test_in_args.count_residues = ["conc"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "c7062408f939f4b310f2f97c3e94eb37"


# ######################  '-dgn' '--degenerate_sequence'################### #
def test_degenerate_sequence_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.degenerate_sequence = [False]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == 'b831e901d8b6b1ba52bad797bad92d14'

    test_in_args.degenerate_sequence = [2, 7]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == '72373f8356051e2c6b67642451379054'

    test_in_args.degenerate_sequence = [100]
    with pytest.raises(KeyError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), pass_through=True)
    assert "Could not locate codon dictionary" in str(err)

    test_in_args.degenerate_sequence = [1]
    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('p g'), pass_through=True)
    assert "Nucleic acid sequence required, not protein" in str(err)


# ######################  '-df', '--delete_features' ###################### #
def test_delete_features_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.delete_features = ["donor"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "f84df6a77063c7def13babfaa0555bbf"


# ######################  '-dlg', '--delete_large' ###################### #
def test_delete_large_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.delete_large = 1285
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "25859dc69d46651a1e04a70c07741b35"


# ######################  'dm', '--delete_metadata' ###################### #
def test_delete_metadata_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.delete_metadata = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "544ab887248a398d6dd1aab513bae5b1"


# ######################  '-dr', '--delete_records' ###################### #
def test_delete_records_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.delete_records = ['α1']
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "54e810265a6ecf7a3d140fc806597f93"
    assert sb_helpers.string2hash(err) == "4f420c9128e515dc24031b5075c034e3"

    test_in_args.delete_records = ['α1', 'α2']
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "eca4f181dae3d7998464ff71e277128f"
    assert sb_helpers.string2hash(err) == "b3983fac3c2cf15f83650a34a17151da"

    test_in_args.delete_records = ['α1', 'α2', "3"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "eca4f181dae3d7998464ff71e277128f"
    assert sb_helpers.string2hash(err) == "7e0929af515502484feb4b1b2c35eaba"

    test_in_args.delete_records = ['foo']
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "b831e901d8b6b1ba52bad797bad92d14"
    assert sb_helpers.string2hash(err) == "553348fa37d9c67f4ce0c8c53b578481"

    temp_file = br.TempFile()
    temp_file.write("α1\nα2")
    test_in_args.delete_records = [temp_file.path, "3"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "eca4f181dae3d7998464ff71e277128f"
    assert sb_helpers.string2hash(err) == "7e0929af515502484feb4b1b2c35eaba"


# ######################  '-drp', '--delete_repeats' ###################### #
def test_delete_repeats_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.delete_repeats = [None]
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy(sb_odd_resources['duplicate']), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "df8e5f139ff41e1d81a082b83c208e12"
    assert sb_helpers.string2hash(err) == "3c27f0df0e892a1c66ed8fef047162ae"

    test_in_args.delete_repeats = [[2, "all"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "b831e901d8b6b1ba52bad797bad92d14"
    assert err == "No duplicate records found\n"

    test_in_args.quiet = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert not err


# ######################  '-ds', '--delete_small' ###################### #
def test_delete_small_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.delete_small = 1285
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "196adf08d4993c51050289e5167dacdf"

    
# ######################  '-efs', '--extract_feature_sequences' ###################### #
def test_extact_feature_sequences_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.extract_feature_sequences = [["CDS"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "7e8a80caf902575c5eb3fc6ba8563956"

    test_in_args.extract_feature_sequences = [["TMD"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "13944b21484d5ea22af4fe57cc8074df"

    test_in_args.extract_feature_sequences = [["TMD", "splice_a"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "78629d308a89b458fb02e71d5568c978"

    test_in_args.extract_feature_sequences = [["foo"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "3cdbd5c8790f12871f8e04e40e315c93"


# ######################  '-fcpg', '--find_cpg' ###################### #
def test_find_cpg_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.find_CpG = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "9499f524da0c35a60502031e94864928"
    assert sb_helpers.string2hash(err) == "1fc07e5884a2a4c1344865f385b1dc79"

    Sb.command_line_ui(test_in_args, Sb.SeqBuddy(">seq1\nATGCCTAGCTAGCT", in_format="fasta"), True)
    out, err = capsys.readouterr()
    assert err == "# No Islands identified\n\n"

    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('p g'), pass_through=True)
    assert "DNA sequence required, not protein or RNA" in str(err)


# ######################  '-fp', '--find_pattern' ###################### #
def test_find_pattern_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.find_pattern = ["ATg{2}T", "tga.{1,6}tg"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), True)
    out, err = capsys.readouterr()

    assert sb_helpers.string2hash(out) == "ec43ce98c9ae577614403933b2c5f37a"
    assert sb_helpers.string2hash(err) == "59fbef542d89ac72741c4d0df73d5f5a"

    test_in_args.find_pattern = ["ATGGN{6}", "ambig"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one("d g"), True)
    out, err = capsys.readouterr()

    assert sb_helpers.string2hash(out) == "ac9adb42fbfa9cf22f033e9a02130985"
    assert sb_helpers.string2hash(err) == "f54ddf323e0d8fecb2ef52084d048531"


# ######################  '-frp', '--find_repeats' ###################### #
def test_find_repeats_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.find_repeats = [True]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert "#### No records with duplicate IDs ####" in out and "#### No records with duplicate sequences ####" in out

    tester = Sb.SeqBuddy(sb_odd_resources['duplicate'])
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "58a57c8151c3591fbac2b94353038a55"

    test_in_args.find_repeats = [2]
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "b34b99828596a5a46c6ab244c6ccc6f6"


# ######################  '-frs', '--find_restriction_sites' ###################### #
def test_find_restriction_sites_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.find_restriction_sites = [["MaeI", "BseRI", "BccI", "MboII", 3, 4, 2, 5, "alpha"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "b06ef2b0a4814fc43a0688f05825486a"
    assert sb_helpers.string2hash(err) == "a240a6db9dfc1f2257faa80bc4b1445b"

    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('p g'), pass_through=True)
    assert "Unable to identify restriction sites in protein sequences." in str(err)


# ######################  '-gbp', '--group_by_prefix' ###################### #
def test_group_by_prefix_ui(capsys, sb_odd_resources):
    tester = Sb.SeqBuddy(sb_odd_resources['cnidaria_pep'])
    test_in_args = deepcopy(in_args)
    test_in_args.group_by_prefix = [[TEMP_DIR.path]]
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert out == ""
    assert "New file: " in err
    assert "Ate.nex" in err
    for prefix in ["Ate", "Hvu", "Che", "Ael", "Cla", "Hec", "Pph", "Nbi", "Ccr"]:
        assert os.path.isfile("%s/%s.nex" % (TEMP_DIR.path, prefix))
        os.unlink("%s/%s.nex" % (TEMP_DIR.path, prefix))

    test_in_args.group_by_prefix = [[TEMP_DIR.path, "u", "h"]]
    Sb.command_line_ui(test_in_args, tester, True)
    for prefix in ["Unknown", "Hv", "C", "Pp"]:
        assert os.path.isfile("%s/%s.nex" % (TEMP_DIR.path, prefix))
        os.unlink("%s/%s.nex" % (TEMP_DIR.path, prefix))

    test_in_args.group_by_prefix = [[TEMP_DIR.path, 1]]
    Sb.command_line_ui(test_in_args, tester, True)
    for prefix in ["A", "H", "C", "P", "N"]:
        assert os.path.isfile("%s/%s.nex" % (TEMP_DIR.path, prefix))
        os.unlink("%s/%s.nex" % (TEMP_DIR.path, prefix))

    test_in_args.group_by_prefix = [[TEMP_DIR.path, "l", 3]]
    Sb.command_line_ui(test_in_args, tester, True)
    for prefix in ["Unknown", "Ae", "C"]:
        assert os.path.isfile("%s/%s.nex" % (TEMP_DIR.path, prefix))
        os.unlink("%s/%s.nex" % (TEMP_DIR.path, prefix))


# ######################  '-gbr', '--group_by_regex' ###################### #
def test_group_by_regex_ui(capsys, sb_odd_resources):
    tester = Sb.SeqBuddy(sb_odd_resources['cnidaria_pep'])
    test_in_args = deepcopy(in_args)
    test_in_args.group_by_regex = [[TEMP_DIR.path]]
    with pytest.raises(ValueError) as err:
        Sb.command_line_ui(test_in_args, tester, pass_through=True)
    assert "You must provide at least one regular expression." in str(err)

    test_in_args.group_by_regex = [[TEMP_DIR.path, "Ate"]]
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert "New file: " in err
    assert "Ate.nex" in err
    for prefix in ["Unknown", "Ate"]:
        assert os.path.isfile("%s/%s.nex" % (TEMP_DIR.path, prefix))
        os.unlink("%s/%s.nex" % (TEMP_DIR.path, prefix))


# ######################  '-gf', '--guess_format' ###################### #
def test_guess_alpha_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.guess_alphabet = True
    test_in_args.sequence = sorted(sb_resources.get_list("d p r f", mode='paths'))
    test_in_args.sequence += [sb_odd_resources["gibberish"], sb_odd_resources["figtree"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "3a2edec76860e60f4f5b8b16b6d32b82", print(out)

    text_io = io.open(sb_resources.get_one("d e", mode='paths'), "r")
    test_in_args.sequence = [text_io]
    tester = Sb.SeqBuddy(text_io)
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert out == "PIPE\t-->\tdna\n"

    temp_file = br.TempFile()
    temp_file.write(">seq1\n123456789")
    text_io = io.open(temp_file.path, "r")
    test_in_args.sequence = [text_io]
    tester = Sb.SeqBuddy(text_io)
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert out == "PIPE\t-->\tUndetermined\n"


# ######################  '-gf', '--guess_format' ###################### #
def test_guess_format_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.guess_format = True
    test_in_args.sequence = sorted(sb_resources.get_list("d f g n py pr psr pss x s c e", mode='paths'))
    test_in_args.sequence += [sb_odd_resources["gibberish"], sb_odd_resources["figtree"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "94082594e3c0aafbcafcd3fd501497ac", print(out)

    text_io = io.open(sb_resources.get_one("d e", mode='paths'), "r")
    test_in_args.sequence = [text_io]
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy, True)
    out, err = capsys.readouterr()
    assert out == "PIPE\t-->\tembl\n"


# ######################  '-hsi', '--hash_seq_ids' ###################### #
def test_hash_seq_ids_ui(capsys, sb_resources):
    test_in_args = deepcopy(in_args)
    test_in_args.hash_seq_ids = [None]
    tester = sb_resources.get_one('d f')
    ids = [rec.id for rec in tester.records]
    Sb.command_line_ui(test_in_args, tester, True)
    for indx, rec in enumerate(tester.records):
        assert rec.id != ids[indx]
        assert ids[indx] == tester.hash_map[rec.id]

    test_in_args.hash_seq_ids = [0]
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert "Warning: The hash_length parameter was passed in with the value 0. This is not a positive integer" in err

    tester.records *= 10
    test_in_args.hash_seq_ids = [1]
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert "cover all sequences, so it has been increased to 2" in err


# ######################  '-is', '--insert_seq' ###################### #
def test_insert_seqs_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.insert_seq = [["DYKDDDDK"]]
    tester = sb_resources.get_one('p f')
    with pytest.raises(AttributeError) as err:
        Sb.command_line_ui(test_in_args, tester, pass_through=True)
    assert "The insert_seq tool requires at least two arguments (sequence and position)" in str(err)

    test_in_args.insert_seq = [[4, "DYKDDDDK"]]
    with pytest.raises(AttributeError) as err:
        Sb.command_line_ui(test_in_args, tester, pass_through=True)
    assert "The first argment must be your insert sequence, not location." in str(err)

    test_in_args.insert_seq = [["DYKDDDDK", "Foo"]]
    with pytest.raises(AttributeError) as err:
        Sb.command_line_ui(test_in_args, tester, pass_through=True)
    assert "The second argment must be location, not insert sequence or regex." in str(err)

    test_in_args.insert_seq = [["DYKDDDDK", "10", "α[23]", "α6"]]
    tester = sb_resources.get_one('p f')
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "345836c75922e5e2a7367c7f7748b591"


# ######################  '-ip', '--isoelectric_point' ###################### #
def test_isoelectric_point_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.isoelectric_point = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "2b0de14da980b6b2c155c34f41da814e"
    assert sb_helpers.string2hash(err) == "402411565abc86649581bf7ab65535b8"

    Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "d1ba12963ee508bc64b64f63464bfb4a"
    assert err == "ID\tpI\n"


# ######################  '-li', '--list_ids' ###################### #
def test_list_ids_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.list_ids = [3]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "53d5d7afd8f15a1a0957f5d5a29cbdc4"


# ######################  '-lf', '--list_features' ###################### #
def test_list_features_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.list_features = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "b99acb13c76f86bcd4e8dc15b97fa11d"

    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "4e37613d1916aa7653d3fec37fc9e368"


# ######################  '-lc', '--lowercase' and 'uc', '--uppercase'  ###################### #
def test_lower_and_upper_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.uppercase = True
    tester = sb_resources.get_one('d f')
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "25073539df4a982b7f99c72dd280bb8f"

    test_in_args.uppercase = False
    test_in_args.lowercase = True
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "b831e901d8b6b1ba52bad797bad92d14"


# ######################  '-mui', '--make_ids_unique' ###################### #
def test_make_ids_unique_ui(capsys, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.make_ids_unique = [[]]
    tester = Sb.SeqBuddy(sb_odd_resources['duplicate'])
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "363c7ed14be59bcacede092b8f334a52"

    test_in_args.make_ids_unique = [["-", 4]]
    tester = Sb.SeqBuddy(sb_odd_resources['duplicate'])
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "0054df3003ba16287159147f3b85dc7b"

    test_in_args.make_ids_unique = [[4, "-"]]
    tester = Sb.SeqBuddy(sb_odd_resources['duplicate'])
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "0054df3003ba16287159147f3b85dc7b"


# ######################  '-fn2p', '--map_features_nucl2prot' ###################### #
def test_map_features_nucl2prot_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.map_features_nucl2prot = True
    test_in_args.sequence = [sb_resources.get_one("d g", mode='paths'), sb_resources.get_one("p f", mode='paths')]
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "5216ef85afec36d5282578458a41169a"

    test_in_args.sequence = [sb_resources.get_one("p f", mode='paths'), sb_resources.get_one("d g", mode='paths')]
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "5216ef85afec36d5282578458a41169a"

    test_in_args.sequence = [sb_resources.get_one("p f", mode='paths'), sb_resources.get_one("d g", mode='paths')]
    test_in_args.out_format = "embl"
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "4f86356e79fa4beb79961ce37b5aa19a"

    with pytest.raises(RuntimeError) as err:
        test_in_args.sequence = [sb_resources.get_one("d g", mode='paths'), sb_odd_resources['duplicate']]
        Sb.command_line_ui(test_in_args, Sb.SeqBuddy, pass_through=True)
    assert "There are repeat IDs in self.records" in str(err)

    with pytest.raises(ValueError) as err:
        test_in_args.sequence = [sb_resources.get_one("d g", mode='paths')]
        Sb.command_line_ui(test_in_args, Sb.SeqBuddy, pass_through=True)
    assert "You must provide one DNA file and one protein file" in str(err)

    with pytest.raises(ValueError) as err:
        test_in_args.sequence = [sb_resources.get_one("d g", mode='paths'), sb_resources.get_one("d f", mode='paths')]
        Sb.command_line_ui(test_in_args, Sb.SeqBuddy, pass_through=True)
    assert "You must provide one DNA file and one protein file" in str(err)


# ######################  '-fp2n', '--map_features_prot2nucl' ###################### #
def test_map_features_prot2nucl_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.map_features_prot2nucl = True
    test_in_args.sequence = [sb_resources.get_one("d f", mode='paths'), sb_resources.get_one("p g", mode='paths')]
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "3ebc92ca11505489cab2453d2ebdfcf2"

    test_in_args.sequence = [sb_resources.get_one("p g", mode='paths'), sb_resources.get_one("d f", mode='paths')]
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "3ebc92ca11505489cab2453d2ebdfcf2"

    test_in_args.sequence = [sb_resources.get_one("p g", mode='paths'), sb_resources.get_one("d f", mode='paths')]
    test_in_args.out_format = "embl"
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "bbbfc9ebc83d3abe3bb3160a38d208e3"

    with pytest.raises(RuntimeError) as err:
        temp_file = br.TempFile()
        duplicate_seqs = Sb.SeqBuddy(sb_odd_resources['duplicate'])
        Sb.back_translate(duplicate_seqs)
        duplicate_seqs.write(temp_file.path)
        test_in_args.sequence = [sb_resources.get_one("p g", mode='paths'), temp_file.path]
        Sb.command_line_ui(test_in_args, Sb.SeqBuddy, pass_through=True)
    assert "There are repeat IDs in self.records" in str(err)

    with pytest.raises(ValueError) as err:
        test_in_args.sequence = [sb_resources.get_one("p g", mode='paths')]
        Sb.command_line_ui(test_in_args, Sb.SeqBuddy, pass_through=True)
    assert "You must provide one DNA file and one protein file" in str(err)

    with pytest.raises(ValueError) as err:
        test_in_args.sequence = [sb_resources.get_one("p g", mode='paths'), sb_resources.get_one("p f", mode='paths')]
        Sb.command_line_ui(test_in_args, Sb.SeqBuddy, pass_through=True)
    assert "You must provide one DNA file and one protein file" in str(err)


# ######################  '-mg', '--merge' ###################### #
def test_merge_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.merge = True
    test_in_args.sequence = [sb_odd_resources["dummy_feats"], sb_resources.get_one("d g", mode='paths')]
    Sb.command_line_ui(test_in_args, Sb.SeqBuddy, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "bae5aeb130b3d5319378a122a6f61df5"

    with pytest.raises(RuntimeError) as err:
        test_in_args.sequence = [sb_resources.get_one("p g", mode='paths'), sb_resources.get_one("d g", mode='paths')]
        Sb.command_line_ui(test_in_args, Sb.SeqBuddy, pass_through=True)
    assert "Sequence mismatch for record 'Mle-Panxα9'" in str(err)


# ######################  '-mw', '--molecular_weight' ###################### #
def test_molecular_weight_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.molecular_weight = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "7a456f37b9d7a780dfe81e453f2e9525"
    assert err == "ID\tssDNA\tdsDNA\n"

    Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "d1014a98fe227f8847ed7478bbdfc857"
    assert err == "ID\tProtein\n"

    Sb.command_line_ui(test_in_args, Sb.SeqBuddy(sb_odd_resources['ambiguous_rna']), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "55ff25f26504c5360557c2dfeb041036"
    assert err == "ID\tssRNA\n"


# ######################  '-ns', '--num_seqs' ###################### #
def test_num_seqs_ui(capsys, sb_resources):
    test_in_args = deepcopy(in_args)
    test_in_args.num_seqs = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert out == '13\n'


# ######################  '-ofa', '--order_features_alphabetically' ###################### #
def test_order_features_alphabetically_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.order_features_alphabetically = [True]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == '21547b4b35e49fa37e5c5b858808befb'

    test_in_args.order_features_alphabetically = ["rev"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == '3b718ec3cb794bcb658d900e517110cc'


# ######################  '-ofp', '--order_features_by_position' ###################### #
def test_order_features_by_position_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.order_features_by_position = [True]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == '2e02a8e079267bd9add3c39f759b252c'

    test_in_args.order_features_by_position = ["rev"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == '4345a14fe27570b3c837c30a8cb55ea9'


# ######################  '-oi', '--order_ids' ###################### #
def test_order_ids_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.order_ids = [True]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == 'c0d656543aa5d20a266cffa790c035ce'

    test_in_args.order_ids = ["rev"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == '2507c667a304fdc003bc68255e094d7b'


# ######################  '-oir', '--order_ids_randomly' ###################### #
def test_order_ids_randomly_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.order_ids_randomly = [True]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) != sb_helpers.seqs2hash(sb_resources.get_one('d f'))

    tester = Sb.order_ids(Sb.SeqBuddy(out))
    assert sb_helpers.seqs2hash(tester) == sb_helpers.seqs2hash(Sb.order_ids(sb_resources.get_one('d f')))


# ######################  '-psc', '--prosite_scan' ###################### #
def test_prosite_scan_ui(capsys, sb_resources, sb_helpers, monkeypatch):
    def mock_raise_urlerror(*args, **kwargs):
        print("mock_raise_urlerror\nargs: %s\nkwargs: %s" % (args, kwargs))
        raise urllib.error.URLError("Fake URLError from Mock")

    def mock_raise_urlerror_8(*args, **kwargs):
        print("mock_raise_urlerror\nargs: %s\nkwargs: %s" % (args, kwargs))
        raise urllib.error.URLError("Fake URLError from Mock: Errno 8")

    monkeypatch.setattr(Sb.PrositeScan, "run", lambda _: sb_resources.get_one("p g"))
    test_in_args = deepcopy(in_args)
    test_in_args.prosite_scan = ['']
    seqbuddy = sb_resources.get_one('d f')

    Sb.command_line_ui(test_in_args, seqbuddy, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "7a8e25892dada7eb45e48852cbb6b63d"

    test_in_args.out_format = "fasta"
    Sb.command_line_ui(test_in_args, seqbuddy, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "c10d136c93f41db280933d5b3468f187"

    monkeypatch.setattr(Sb.PrositeScan, "run", mock_raise_urlerror_8)
    with pytest.raises(urllib.error.URLError):
        Sb.command_line_ui(test_in_args, seqbuddy, pass_through=True)
    out, err = capsys.readouterr()
    assert "Unable to contact EBI, are you connected to the internet?" in out

    monkeypatch.setattr(Sb.PrositeScan, "run", mock_raise_urlerror)
    with pytest.raises(urllib.error.URLError) as err:
        Sb.command_line_ui(test_in_args, seqbuddy, pass_through=True)
    assert "Fake URLError from Mock" in str(err)


# ######################  '-prr', '--pull_random_recs' ###################### #
def test_pull_random_recs_ui(capsys, sb_resources):
    test_in_args = deepcopy(in_args)
    test_in_args.pull_random_record = [True]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    tester = Sb.SeqBuddy(out)
    assert len(tester.records) == 1
    assert tester.records[0].id in sb_resources.get_one('d f').to_dict()

    test_in_args.pull_random_record = [20]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    tester = Sb.SeqBuddy(out)
    assert len(tester.records) == 13
    assert sorted([rec.id for rec in tester.records]) == sorted([rec.id for rec in sb_resources.get_one('d f').records])


# ######################  '-pr', '--pull_record_ends' ###################### #
def test_pull_record_ends_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.pull_record_ends = 10
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "754d6868030d1122b35386118612db72"

    test_in_args.pull_record_ends = -10
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "9cfc91c3fdc5cd9daabce0ef9bac2db7"


# ######################  '-pr', '--pull_records' ###################### #
def test_pull_records_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.pull_records = ["α1"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "db52337c628fd8d8d70a5581355c51a5"

    test_in_args.pull_records = ["α1", "α2"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "cd8d7284f039233e090c16e8aa6b5035"

    temp_file = br.TempFile()
    temp_file.write("α1\nα2")
    test_in_args.pull_records = [temp_file.path]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "cd8d7284f039233e090c16e8aa6b5035"


# ######################  '-prf', '--pull_records_with_feature' ###################### #
def test_pull_records_with_feature_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.pull_records_with_feature = ["splice_acceptor"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "36757409966ede91ab19deb56045d584"

    test_in_args.pull_records_with_feature = ["CDS", "splice_acceptor"]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "0907009d491183f6d70531c0186c96d7"

    temp_file = br.TempFile()
    temp_file.write("CDS\nsplice_acceptor")
    test_in_args.pull_records_with_feature = [temp_file.path]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "0907009d491183f6d70531c0186c96d7"


# ######################  '-prg', '--purge' ###################### #
def test_purge_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.purge = 200
    Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "b21b2e2f0ca1fcd7b25efbbe9c08858c"
    assert sb_helpers.string2hash(err) == "fbfde496ae179f83e3d096da15d90920"


# ######################  '-ri', '--rename_ids' ###################### #
def test_rename_ids_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.rename_ids = [["[a-z](.)", "?\\1", 2]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "f12c44334b507117439928c529eb2944"

    test_in_args.rename_ids = [["[a-z](.)"]]
    with pytest.raises(AttributeError) as err:
        Sb.command_line_ui(test_in_args, Sb.SeqBuddy, pass_through=True)
    assert "Please provide at least a query and a replacement string" in str(err)

    test_in_args.rename_ids = [["[a-z](.)", "?\\1", "foo"]]
    with pytest.raises(ValueError) as err:
        Sb.command_line_ui(test_in_args, Sb.SeqBuddy, pass_through=True)
    assert "Max replacements argument must be an integer" in str(err)

    test_in_args.rename_ids = [["[a-z](.)", "?\\1\\2", 2]]
    with pytest.raises(AttributeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), pass_through=True)
    assert "There are more replacement match values specified than query parenthesized groups" in str(err)

    test_in_args.rename_ids = [["[a-z](.)", "?\\1", 2, "store"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "54f65b222f7dd2db010d73054dbbd0a9"

    test_in_args.rename_ids = [["[a-z](.)", "?\\1", "store", 2]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "54f65b222f7dd2db010d73054dbbd0a9"

    test_in_args.rename_ids = [["[a-z](.)", "?\\1", 2, "store"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "7e14a33700db6a32b1a99f0f9fd76f53"


# ######################  '-rs', '--replace_subseq' ###################### #
def test_replace_subseq_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.replace_subseq = [["atg(.{5}).{3}", "FOO\\1BAR"]]
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "4e1b13745d256331ccb46dd275627edb"


# ######################  '-rc', '--reverse_complement' ###################### #
def test_reverse_complement_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.reverse_complement = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d g'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "47941614adfcc5bd107f71abef8b3e00"

    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('p g'), pass_through=True)
    assert "SeqBuddy object is protein. Nucleic acid sequences required." in str(err)

    tester = Sb.SeqBuddy(sb_odd_resources['mixed'])
    tester.alpha = IUPAC.ambiguous_dna
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "efbcc71f3b2820ea05bf32038012b883"

    tester.records[0].seq.alphabet = IUPAC.protein
    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, tester, pass_through=True)
    assert "Record 'Mle-Panxα12' is protein. Nucleic acid sequences required." in str(err)


# ######################  '-r2d', '--reverse_transcribe' ###################### #
def test_reverse_transcribe_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.reverse_transcribe = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('r f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "b831e901d8b6b1ba52bad797bad92d14"

    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), pass_through=True)
    assert "RNA sequence required, not IUPACAmbiguousDNA()." in str(err)


# ######################  '-sf', '--screw_formats' ###################### #
hashes = [("fasta", "09f92be10f39c7ce3f5671ef2534ac17"), ("gb", "26718f0a656116bfd0a7f6c03d270ecf"),
          ("nexus", "2822cc00c2183a0d01e3b79388d344b3"), ("phylip", "6a4d62e1ee130b324cce48323c6d1d41"),
          ("phylip-relaxed", "4c2c5900a57aad343cfdb8b35a8f8442"), ("phylipss", "089cfb52076e63570597a74b2b000660"),
          ("phylipsr", "58a74f5e08afa0335ccfed0bdd94d3f2"), ("stockholm", "8c0f5e2aea7334a0f2774b0366d6da0b"),
          ("raw", "f0ce73f4d05a5fb3d222fb0277ff61d2")]


@pytest.mark.parametrize("_format,next_hash", hashes)
def test_screw_formats_ui(_format, next_hash, capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.screw_formats = _format
    tester = Sb.pull_recs(sb_resources.get_one('d n'), "α[2-9]")
    Sb.command_line_ui(test_in_args, Sb.make_copy(tester), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == next_hash


def test_screw_formats_ui2(sb_resources):
    test_in_args = deepcopy(in_args)
    test_in_args.screw_formats = "foo"
    with pytest.raises(OSError) as err:
        Sb.command_line_ui(test_in_args, Sb.SeqBuddy, pass_through=True)
    assert "Error: unknown format" in str(err)

    sb_resources.get_one('d f').write("%s/seq.fa" % TEMP_DIR.path)
    test_in_args.sequence = ["%s/seq.fa" % TEMP_DIR.path]
    test_in_args.screw_formats = "genbank"
    test_in_args.in_place = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    assert os.path.isfile("%s/seq.gb" % TEMP_DIR.path)


# ######################  '-sfr', '--select_frame' ###################### #
def test_select_frame_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    tester = sb_resources.get_one('d g')
    test_in_args.select_frame = 1
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "908744b00d9f3392a64b4b18f0db9fee"

    test_in_args.select_frame = 2
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "08fe54a87249f5fb9ba22ff6d0053787"

    test_in_args.select_frame = 3
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "cfe2d405487d69dceb2a11dd44ceec59"

    test_in_args.select_frame = 1
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "908744b00d9f3392a64b4b18f0db9fee"

    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), pass_through=True)
    assert "Select frame requires nucleic acid, not protein" in str(err)


# ######################  '-ss', '--shuffle_seqs' ###################### #
def test_shuffle_seqs_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    tester = sb_resources.get_one('d f')
    test_in_args.shuffle_seqs = True
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) != "b831e901d8b6b1ba52bad797bad92d14"


# ######################  '-d2r', '--transcribe' ###################### #
def test_transcribe_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.transcribe = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "d2db9b02485e80323c487c1dd6f1425b"

    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), pass_through=True)
    assert "DNA sequence required, not IUPACProtein()." in str(err)


# ######################  '-tr', '--translate' ###################### #
def test_translate_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.translate = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "06893e14839dc0448e6f522c1b8f8957"

    Sb.command_line_ui(test_in_args, Sb.SeqBuddy(sb_odd_resources["ambiguous_rna"]), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "648ccc7c3400882be5bf6e8d9781f74e"

    tester = Sb.SeqBuddy(sb_odd_resources['mixed'])
    tester.alpha = IUPAC.ambiguous_dna
    tester.records[0].seq.alphabet = IUPAC.protein
    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, tester, pass_through=True)
    assert 'Record Mle-Panxα12 is protein.' in str(err)

    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), pass_through=True)
    assert "Nucleic acid sequence required, not protein." in str(err)


# ######################  '-tr6', '--translate6frames' ###################### #
def test_translate6frames_ui(capsys, sb_resources, sb_odd_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.translate6frames = True
    Sb.command_line_ui(test_in_args, sb_resources.get_one('d f'), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "95cf24202007399e6ccd6e6f33ae012e"

    Sb.command_line_ui(test_in_args, Sb.SeqBuddy(sb_odd_resources["ambiguous_rna"]), True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "6d3fcad0ea417014bc825cedd354fd26"
    assert err == ""

    tester = Sb.SeqBuddy(sb_odd_resources["mixed"])
    tester.alpha = IUPAC.ambiguous_dna
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "b54ec5c49bd88126de337e1eb3d2ad23"

    tester.records[0].seq.alphabet = IUPAC.protein
    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, tester, pass_through=True)
    assert "Record 'Mle-Panxα12' is protein. Nucleic acid sequences required." in str(err)

    with pytest.raises(TypeError) as err:
        Sb.command_line_ui(test_in_args, sb_resources.get_one('p f'), pass_through=True)
    assert "You need to supply DNA or RNA sequences to translate" in str(err)

'''
# ######################  '-tmd', '--transmembrane_domains' ###################### #
@pytest.mark.internet
@pytest.mark.slow
@pytest.mark.foo1
def test_transmembrane_domains_ui(capsys, sb_resources, sb_helpers):
    test_in_args = deepcopy(in_args)
    test_in_args.transmembrane_domains = [True]
    test_in_args.quiet = True
    tester = sb_resources.get_one("p f")
    Sb.pull_recs(tester, "Panxα[234]")
    Sb.command_line_ui(test_in_args, tester, True)
    out, err = capsys.readouterr()
    assert sb_helpers.string2hash(out) == "7285d3c6d60ccb656e39d6f134d1df8b"

    test_in_args.quiet = False
    tester = Sb.SeqBuddy(">rec\n%s" % ("M" * 9437174))
    with pytest.raises(ValueError) as err:
        Sb.command_line_ui(test_in_args, tester, pass_through=True)
    assert "Record 'rec' is too large to send to TOPCONS." in str(err)

'''
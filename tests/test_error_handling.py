import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core'))
import main
import parser
from core import diagnostics
from py2bs import translate
from py2bs.verify import run_brittainscript


class ErrorHandlingTests(unittest.TestCase):
    def setUp(self):
        self.saved_names = dict(parser.names)
        self.saved_functions = dict(main.functions)

    def tearDown(self):
        parser.names.clear()
        parser.names.update(self.saved_names)
        main.functions.clear()
        main.functions.update(self.saved_functions)
        self.assertEqual(len(parser.scopes), 1)
        self.assertEqual(main.function_environments, [None])

    def run_bs(self, source, file='test.bs'):
        source = textwrap.dedent(source).strip('\n')
        lines = [diagnostics.SourceLine(text, file, index)
                 for index, text in enumerate(source.splitlines(), 1)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.execute_lines(lines)
        return output.getvalue()

    def test_typed_catch_stops_the_failed_block_and_runs_finally(self):
        self.assertEqual(self.run_bs('''
            try:
                result = 10 / 0
                push("unreachable")
            catch ValueError:
                push("wrong handler")
            catch ArithmeticError as problem:
                push(problem.type)
                push(problem.message)
            finally:
                push("cleanup")
            end
            push("after")
        '''), 'ZeroDivisionError\ndivision by zero\ncleanup\nafter\n')
        self.assertNotIn('result', parser.names)
        self.assertNotIn('problem', parser.names)

    def test_catch_all_and_custom_error(self):
        self.assertEqual(self.run_bs('''
            try:
                raise error("invalid record", "ValidationError")
            catch ValidationError as problem:
                push(problem.message)
            end
            try:
                raise "stopped"
            catch as problem:
                push(problem.type)
            end
        '''), 'invalid record\nRuntimeError\n')

    def test_caught_errors_do_not_emit_or_fail_verification(self):
        result = run_brittainscript('try:\n    push(1 / 0)\ncatch:\n    push("ok")\nend\n')
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.stdout, 'ok\n')
        with diagnostics.capture_errors() as errors:
            self.run_bs('try:\n    raise "handled"\ncatch:\nend')
        self.assertEqual(errors, [])

    def test_runtime_failures_have_catchable_types(self):
        cases = [
            ('1 / 0', 'ZeroDivisionError'), ('1 // 0', 'ZeroDivisionError'),
            ('1 % 0', 'ZeroDivisionError'), ('"a" + 1', 'TypeError'),
            ('1 - "a"', 'TypeError'), ('1 < "a"', 'TypeError'),
            ('sqrroot(0 - 1)', 'ValueError'), ('unknown_error_name', 'NameError'),
            ('unknown_error_function()', 'NameError'), ('len(1)', 'TypeError'),
            ('len()', 'TypeError'), ('tonum("bad")', 'ValueError'),
            ('[1][8]', 'IndexError'), ('[1]["a"]', 'TypeError'),
            ('[].pop()', 'IndexError'), ('[1].remove(2)', 'ValueError'),
            ('"a".contains()', 'TypeError'), ('"a".unknown()', 'AttributeError'),
            ('error(1)', 'TypeError'), ('error("bad", "invalid-type")', 'ValueError'),
            ('pyimport("missing_bs_error_test_module")', 'ModuleNotFoundError'),
            ('pyimport("math").sqrt(0 - 1)', 'ValueError'),
            ('pyimport("json").loads("{")', 'JSONDecodeError'),
            ('pyimport("builtins").dict()["missing"]', 'KeyError'),
            ('readfile("missing_bs_error_test_file")', 'FileNotFoundError'),
            ('datetime("parse", "bad", "%Y")', 'ValueError'),
        ]
        for expression, kind in cases:
            with self.subTest(expression=expression):
                output = self.run_bs(f'try:\n    discard {expression}\ncatch {kind} as e:\n    push(e.type)\nend')
                self.assertEqual(output, kind + '\n')

    def test_python_callable_and_custom_subclass_keep_their_types(self):
        class ValidationError(ValueError):
            pass

        def fail():
            raise ValidationError('invalid')

        parser.names['python_fail'] = fail
        self.assertEqual(self.run_bs('''
            try:
                python_fail()
            catch ValueError as e:
                push(e.type)
            end
        '''), 'ValidationError\n')

    def test_failed_assignment_and_augmented_assignment_leave_old_value(self):
        self.assertEqual(self.run_bs('''
            value = 9
            try:
                value = tonum("bad")
            catch ValueError:
            end
            try:
                value /= 0
            catch ZeroDivisionError:
            end
            push(value)
        '''), '9\n')

    def test_python_error_messages_keep_their_original_text(self):
        def fail():
            raise ValueError('Error: invalid')

        parser.names['python_fail'] = fail
        self.assertEqual(self.run_bs('''
            try:
                python_fail()
            catch ValueError as e:
                push(e.message)
                push(tostr(e))
            end
        '''), 'Error: invalid\nError: invalid\n')

    def test_unhandled_error_stops_side_effects(self):
        with self.assertRaises(diagnostics.BSError) as raised:
            self.run_bs('value = unknown_error_name\nafter_error = true')
        self.assertEqual(raised.exception.type, 'NameError')
        self.assertNotIn('value', parser.names)
        self.assertNotIn('after_error', parser.names)

    def test_error_location_and_function_stack(self):
        with self.assertRaises(diagnostics.BSError) as raised:
            self.run_bs('''
                func inner():
                    return 1 / 0
                end
                func outer():
                    return inner()
                end
                outer()
            ''', 'trace.bs')
        error = raised.exception
        self.assertEqual((error.file, error.line, error.column), ('trace.bs', 2, 14))
        self.assertEqual([(f.function, f.file, f.line, f.column) for f in error.stack],
                         [('outer', 'trace.bs', 7, 1), ('inner', 'trace.bs', 5, 12)])
        self.assertNotIn('Traceback', error.format())
        self.run_bs('push("next")')
        with self.assertRaises(diagnostics.BSError) as later:
            self.run_bs('raise "new"')
        self.assertEqual(later.exception.stack, [])

    def test_rethrow_preserves_original_location_and_identity(self):
        self.assertEqual(self.run_bs('''
            saved = null
            try:
                try:
                    raise "original"
                catch as e:
                    saved = e
                    raise
                finally:
                    push("cleanup")
                end
            catch as e:
                push(saved == e)
                push(e.line)
            end
        '''), 'cleanup\nTrue\n4\n')

    def test_error_constructor_location_is_the_raise_statement(self):
        with self.assertRaises(diagnostics.BSError) as raised:
            self.run_bs('problem = error("later")\nraise problem')
        self.assertEqual(raised.exception.line, 2)

    def test_finally_runs_for_return_and_can_replace_it(self):
        self.assertEqual(self.run_bs('''
            func first():
                try:
                    return 7
                finally:
                    push("cleanup")
                end
            end
            func second():
                try:
                    return 7
                finally:
                    return 8
                end
            end
            push(first())
            push(second())
        '''), 'cleanup\n7\n8\n')

    def test_finally_runs_for_break_and_continue(self):
        self.assertEqual(self.run_bs('''
            for i in space(3):
                try:
                    cond i == 0:
                        continue
                    end
                    break
                finally:
                    push(i)
                end
            end
            push("after")
        '''), '0\n1\nafter\n')

    def test_errors_in_handlers_go_to_the_outer_handler(self):
        self.assertEqual(self.run_bs('''
            try:
                try:
                    raise error("first", "ValueError")
                catch ValueError:
                    raise error("second", "TypeError")
                catch TypeError:
                    push("wrong")
                finally:
                    push("cleanup")
                end
            catch TypeError as e:
                push(e.message)
            end
        '''), 'cleanup\nsecond\n')

    def test_finally_error_replaces_a_pending_error(self):
        with self.assertRaises(diagnostics.BSError) as raised:
            self.run_bs('try:\n    raise "first"\nfinally:\n    raise "second"\nend')
        self.assertEqual(raised.exception.message, 'second')
        self.assertEqual(raised.exception.line, 4)

    def test_else_only_runs_after_success_and_is_not_caught_by_its_handlers(self):
        self.assertEqual(self.run_bs('''
            try:
                push("body")
            catch:
                push("wrong")
            else:
                push("success")
            finally:
                push("cleanup")
            end
        '''), 'body\nsuccess\ncleanup\n')
        with self.assertRaisesRegex(diagnostics.BSError, 'else failure'):
            self.run_bs('try:\ncatch:\nelse:\n    raise "else failure"\nend')

    def test_error_binding_is_cleared_on_return_or_error(self):
        self.run_bs('''
            try:
                raise "first"
            catch as problem:
                saved_problem = problem
            end
        ''')
        self.assertNotIn('problem', parser.names)
        self.assertEqual(parser.names['saved_problem'].message, 'first')
        with self.assertRaises(diagnostics.BSError):
            self.run_bs('try:\n    raise "first"\ncatch as problem:\n    raise "second"\nend')
        self.assertNotIn('problem', parser.names)

    def test_native_blocks_can_close_on_dedent(self):
        self.assertEqual(self.run_bs('''
            try:
                push(1 / 0)
            catch:
                push("caught")
            finally:
                push("cleanup")
            push("after")
        '''), 'caught\ncleanup\nafter\n')

    def test_invalid_handlers_fail_before_the_body_runs(self):
        cases = [
            'try:\n    marker = 1\nend',
            'try value:\n    marker = 1\ncatch:\nend',
            'try:\n    marker = 1\ncatch:\ncatch ValueError:\nend',
            'try:\n    marker = 1\nfinally:\ncatch:\nend',
            'try:\n    marker = 1\ncatch ValueError as push:\nend',
            'try:\n    marker = 1\ncatch ValueError as for:\nend',
            'try:\n    marker = 1\ncatch ValueError as:\nend',
            'try:\n    marker = 1\nfinally value:\nend',
            'try:\n    marker = 1\nelse:\nfinally:\nend',
            'try:\n    marker = 1\ncatch:\nelse:\nelse:\nend',
        ]
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaises(diagnostics.BSError) as raised:
                    self.run_bs(source)
                self.assertEqual(raised.exception.type, 'SyntaxError')
                self.assertNotIn('marker', parser.names)

    def test_stray_clauses_and_missing_end_are_syntax_errors(self):
        for source in ('catch:', 'finally:', 'try:\n    push(1)'):
            with self.subTest(source=source):
                with self.assertRaises(diagnostics.BSError) as raised:
                    self.run_bs(source)
                self.assertEqual(raised.exception.type, 'SyntaxError')

    def test_invalid_conditional_clause_has_its_own_location(self):
        with self.assertRaises(diagnostics.BSError) as raised:
            self.run_bs('cond false:\nelse invalid:\nend')
        self.assertEqual(raised.exception.line, 2)

    def test_raise_checks_its_argument_and_active_error(self):
        for source, kind in [('raise 3', 'TypeError'), ('raise', 'RuntimeError')]:
            with self.subTest(source=source):
                with self.assertRaises(diagnostics.BSError) as raised:
                    self.run_bs(source)
                self.assertEqual(raised.exception.type, kind)

    def test_lexer_error_location(self):
        with self.assertRaises(diagnostics.BSError) as raised:
            self.run_bs('    push(1$)')
        self.assertEqual(raised.exception.type, 'SyntaxError')
        # run_bs removes common indentation.
        self.assertEqual(raised.exception.column, 7)

    def test_comments_do_not_change_the_error_column(self):
        with self.assertRaises(diagnostics.BSError) as raised:
            self.run_bs('func fail():\n    return 1 / 0 # return 1 / 0\nend\nfail()')
        self.assertEqual((raised.exception.line, raised.exception.column), (2, 14))

    def test_module_errors_keep_the_library_source_location(self):
        with self.assertRaises(diagnostics.BSError) as raised:
            self.run_bs('add math\nmath.factorial("bad")')
        self.assertTrue(raised.exception.file.endswith('/libs/math.bs'))
        self.assertEqual(raised.exception.stack[-1].function, 'factorial')

    def test_repl_reads_try_clauses_and_survives_an_error(self):
        inputs = iter(['raise "failed"', 'try:', 'push(1 / 0)', 'catch:',
                       'push("caught")', 'finally:', 'push("cleanup")', 'end', 'exit'])
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch('builtins.input', side_effect=lambda prompt: next(inputs)):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                main.run_repl()
        self.assertIn('caught\ncleanup\n', output.getvalue())
        self.assertIn('RuntimeError: failed', errors.getvalue())

    def test_gui_callback_errors_reach_the_handler_outside_the_event_loop(self):
        backend = parser.gui_backend
        window = mock.Mock()
        window.mainloop.side_effect = lambda: backend._run_callback('fail_callback', [])
        with mock.patch.object(backend, 'root_window', window), mock.patch.object(backend, 'stop_on_error', True):
            self.assertEqual(self.run_bs('''
                func fail_callback():
                    raise "callback failed"
                end
                try:
                    guirun()
                catch as e:
                    push(e.message)
                    push(e.line)
                end
            '''), 'callback failed\n2\n')
        window.quit.assert_called_once()
        self.assertEqual(backend.callback_error_frames, [])

    def test_a_handler_inside_the_callback_keeps_the_event_loop_running(self):
        backend = parser.gui_backend
        window = mock.Mock()
        window.mainloop.side_effect = lambda: backend._run_callback('handle_callback', [])
        with mock.patch.object(backend, 'root_window', window):
            self.assertEqual(self.run_bs('''
                func handle_callback():
                    try:
                        raise "callback failed"
                    catch:
                        push("handled")
                    end
                end
                guirun()
            '''), 'handled\n')
        window.quit.assert_not_called()
        self.assertEqual(backend.callback_error_frames, [])

    def test_run_file_and_cli_return_failure_without_python_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'failure.bs'
            path.write_text('push("before")\nraise "failed"\npush("after")\n')
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main.run_file(str(path))
            self.assertEqual(status, 1)
            self.assertEqual(output.getvalue(), 'before\n')
            self.assertIn(f'{path}:2:1', errors.getvalue())
            for entry in ([str(ROOT / 'run.py')], [str(ROOT / 'core/main.py')], ['-m', 'core.main']):
                with self.subTest(entry=entry):
                    result = subprocess.run([sys.executable, *entry, str(path)],
                                            capture_output=True, text=True, cwd=ROOT)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, 'before\n')
                    self.assertIn('RuntimeError: failed', result.stderr)
                    self.assertNotIn('Traceback', result.stderr)

    def test_missing_source_file_has_a_clean_diagnostic(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            status = main.run_file('/missing_bs_error_test_file.bs')
        self.assertEqual(status, 1)
        self.assertIn('FileNotFoundError:', errors.getvalue())
        self.assertNotIn('Traceback', errors.getvalue())


class ExceptionTranslationTests(unittest.TestCase):
    def assert_matches(self, source, output):
        result = translate(textwrap.dedent(source).strip() + '\n')
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.bs_stdout, output)

    def test_builtin_errors_and_handler_arguments_match(self):
        self.assert_matches('''
            try:
                raise ValueError("invalid")
            except ValueError as e:
                print(str(e))
                print(e.args[0])
            finally:
                print("cleanup")
        ''', 'invalid\ninvalid\ncleanup\n')

    def test_empty_exception_constructor_and_parent_handler(self):
        self.assert_matches('''
            try:
                raise ZeroDivisionError()
            except ArithmeticError as e:
                print(len(e.args))
        ''', '0\n')

    def test_exception_classes_and_formatted_os_errors(self):
        self.assert_matches('''
            try:
                raise ValueError
            except ValueError as e:
                print(len(e.args))
            try:
                raise OSError(2, "missing")
            except EnvironmentError as e:
                print(str(e))
                print(e.args[0])
        ''', '0\n[Errno 2] missing\n2\n')

    def test_handler_locals_are_deleted(self):
        self.assert_matches('''
            e = "global"
            def handle():
                try:
                    raise ValueError("invalid")
                except ValueError as e:
                    print(str(e))
                try:
                    print(e)
                except UnboundLocalError:
                    print("cleared")
            handle()
            print(e)
        ''', 'invalid\ncleared\nglobal\n')

    def test_bare_raise_nested_handlers_and_finally(self):
        self.assert_matches('''
            try:
                try:
                    raise ValueError("invalid")
                except ValueError:
                    raise
                finally:
                    print("cleanup")
            except Exception:
                print("caught")
        ''', 'cleanup\ncaught\n')

    def test_try_else_and_return(self):
        self.assert_matches('''
            def value():
                try:
                    print("body")
                except ValueError:
                    return 1
                else:
                    return 2
                finally:
                    print("cleanup")
            print(value())
        ''', 'body\ncleanup\n2\n')

    def test_handler_type_tuples_and_chaining_are_rejected(self):
        for source, feature in [
            ('try:\n    pass\nexcept (ValueError, TypeError):\n    pass\n', 'exception handler type'),
            ('raise ValueError() from None', 'exception chaining'),
            ('ValueError = 1', 'exception type binding'),
            ('try:\n    pass\nexcept Exception:\n    pass\nexcept ValueError:\n    pass', 'exception handler order'),
        ]:
            with self.subTest(feature=feature):
                result = translate(source, verify=False)
                self.assertFalse(result.ok)
                self.assertIn(feature, result.rejected_features)


if __name__ == '__main__':
    unittest.main()

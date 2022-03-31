import re
from ansible.plugins.callback import CallbackBase
from ansible import context as ansible_context
from ansible.module_utils.common.collections import ImmutableDict

ansible_context.CLIARGS = ImmutableDict(
    {
        'syntax': False,
        'start_at_task': None,
        'verbosity': 0,
        'become_method': 'sudo'
    }
)


class AnsiblePlayBookResultsCollector(CallbackBase):
    """

    """

    def __init__(self, sock, *args, return_results=None, filter_output=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.playbook_results = []
        self.sock = sock
        self.results = return_results
        self.filter_output = filter_output

    def v2_playbook_on_play_start(self, play):
        if self.filter_output is not None:
            return
        name = play.get_name().strip()
        if not name:
            msg = '\nPLAY {}\n'.format('*' * 100)
        else:
            msg = '\nPLAY [{}] {}\n'.format(name, '*' * 100)
        self.send_save(msg)

    def v2_playbook_on_task_start(self, task, is_conditional):

        if self.filter_output is not None:
            return
        if task.get_name() == 'Gathering Facts':
            return

        msg = '\nTASK [{}] {}\n'.format(task.get_name(), '*' * 100)
        self.send_save(msg)

    def v2_runner_on_ok(self, result, *args, **kwargs):
        task_name = result._task.get_name()

        if self.filter_output is not None and not task_name in self.filter_output:
            return

        if self.filter_output is None:
            if result.is_changed():
                data = '[{}]=> changed'.format(result._host.name)
            else:
                data = '[{}]=> ok'.format(result._host.name)
            self.send_save(
                data, color='yellow' if result.is_changed() else 'green')
        if 'msg' in result._task_fields['args']:
            self.send_save('\n')
            msg = result._task_fields['args']['msg']
            self.send_save(msg, color='white',)
            if self.results:
                for k in self.results.keys():
                    regex = fr'{k}:\s*(?P<data>.*)'
                    match = re.search(regex, msg, flags=re.MULTILINE)
                    if match:
                        self.results[k].append(
                            (result._host.name, match.groupdict()['data']))

    def v2_runner_on_failed(self, result, *args, **kwargs):
        if self.filter_output is not None:
            return
        if 'changed' in result._result:
            del result._result['changed']
        data = 'fail: [{}]=> {}: {}'.format(
            result._host.name, 'failed',
            self._dump_results(result._result)
        )
        self.send_save(data, color='red')

    def v2_runner_on_unreachable(self, result):
        if 'changed' in result._result:
            del result._result['changed']
        data = '[{}]=> {}: {}'.format(
            result._host.name,
            'unreachable',
            self._dump_results(result._result)
        )
        self.send_save(data)

    def v2_runner_on_skipped(self, result):
        if self.filter_output is not None:
            return
        if 'changed' in result._result:
            del result._result['changed']
        data = '[{}]=> {}: {}'.format(
            result._host.name,
            'skipped',
            self._dump_results(result._result)
        )
        self.send_save(data, color='blue')

    def v2_playbook_on_stats(self, stats):
        if self.filter_output is not None:
            return
        hosts = sorted(stats.processed.keys())
        data = '\nPLAY RECAP {}\n'.format('*' * 100)
        self.send_save(data)
        for h in hosts:
            s = stats.summarize(h)
            msg = '{} : ok={} changed={} unreachable={} failed={} skipped={}'.format(
                h, s['ok'], s['changed'], s['unreachable'], s['failures'], s['skipped'])
            self.send_save(msg)

    def send_save(self, data, color=None):
        self.sock.echo(data, color=color)
        self.playbook_results.append(data)

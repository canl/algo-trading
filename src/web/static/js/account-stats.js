function renderStatsLabels(env, account, startFrom) {
  const url = `/api/v1/${env}/account/${account}/stats?start_from=${startFrom}`
  fetch(url).then(function (response) {
    response.json().then(function (payload) {
      let direction = payload.data.pl_pct > 0 ?
        '<i class="fa fa-arrow-up" aria-hidden="true" style="font-size:18px"></i>' :
        '<i class="fa fa-arrow-down" aria-hidden="true" style="font-size:18px;color: #DC3545"></i>'
      ytd.innerHTML = direction + (payload.data.pl_pct * 100).toFixed(2) + '%';
      payload.data.pl_pct > 0 ? ytd.classList.add("text-success") : ytd.classList.add("text-danger");

      rpl.textContent = '£' + numberWithCommas(payload.data.pl.toFixed(2))
      payload.data.pl > 0 ? rpl.classList.add("text-success") : rpl.classList.add("text-danger");

      upl.textContent = '£' + numberWithCommas(payload.data.unrealized_pL.toFixed(2))
      payload.data.unrealized_pL > 0 ? upl.classList.add("text-success") : upl.classList.add("text-danger");

      pf.textContent = payload.data.profit_factor.toFixed(2)
      if (payload.data.profit_factor > 2) {
        pf.classList.add("text-success")
      } else if (payload.data.profit_factor > 1) {
        pf.classList.add("text-warning")
      } else {
        pf.classList.add("text-danger")
      }

      ib.textContent = '£' + numberWithCommas(payload.data.initial_balance.toFixed(0))

      //Render knob
      $('.dial').val(payload.data.win_percent * 100).trigger('change')
    });
  });
}
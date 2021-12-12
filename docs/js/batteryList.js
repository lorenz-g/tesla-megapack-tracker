

function generateBatteryList(order, columns, summary, listId){
    $(listId).DataTable({
        "pageLength": 25,
        "order": [[ order, "desc" ]],
        // the inspiration for the totals row comes from https://elbilstatistikk.no/
        'drawCallback': function (oSettings) {
            var api = this.api();
            var searchStr = oSettings.oPreviousSearch.sSearch;
            searchStr = searchStr.trim();

            if (searchStr.length != 0) {
                for (var i = 0; i < columns.length; i++) {
                    var nodes = api.column(columns[i], { filter: 'applied', page: 'current' }).nodes();
                    var total = 0;
                    for (var j = 0; j < nodes.length; j++) {
                        total += parseFloat(nodes[j].innerText) || 0
                    }
                    $('tfoot th').eq(columns[i]).html(total);
                }
                var pLen = api.column(columns[i], { filter: 'applied', page: 'current' }).nodes().length
                $('tfoot th').eq(0).html(`Total (${pLen} projects)`);
            }
            else {
                $('tfoot th').eq(0).html(`Total (${summary.totals_row.count} projects)`);
                $('tfoot th').eq(6).html(`${summary.totals_row.mwh}`);
                $('tfoot th').eq(7).html(`${summary.totals_row.mw}`);
            }
        } //end footerCallback
    });

}
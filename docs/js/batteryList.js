

function generateBatteryList(order, mwh_column, mw_column, listId){

    // the 768 equals the md bootstrap breakpoint
    // https://getbootstrap.com/docs/5.3/layout/breakpoints/#available-breakpoints
    // This is different on Chrome
    // console.log(window.innerWidth);
    // console.log(document.documentElement.clientWidth);

    // had an error with chrome on mobile where the innerwidth would be the width including the overflow from the table
    // with table: ca 800px, without it 398
    // that's hwy using the clientWidth below

    // not that this will not change when resizing the browser but that's ok now...
    if (document.documentElement.clientWidth < 768){
        var scrollX = true;
        var pageLength = 10;
        var pagingType = "numbers";
    } else {
        var scrollX = false;
        var pageLength = 25;
        var pagingType = "simple_numbers";
    }

    $(listId).DataTable({
        "pageLength": pageLength,
        // https://datatables.net/reference/option/pagingType
        "pagingType": pagingType,
        "order": [[ order, "desc" ]],
        // for the table on mobile that you can scroll in the x direction
        "scrollX": scrollX,
        // code from here: https://datatables.net/examples/advanced_init/footer_callback.html
        footerCallback: function (row, data, start, end, display) {
            let api = this.api();
     
            // Remove the formatting to get integer data for summation
            let intVal = function (i) {
                return typeof i === 'string'
                    ? i.replace(/[\$,]/g, '') * 1
                    : typeof i === 'number'
                    ? i
                    : 0;
            };
            
            // mwh
            // Total over all pages
            total = api
                .column(mwh_column, {filter: 'applied'})
                .data()
                .reduce((a, b) => intVal(a) + intVal(b), 0);
     
            // Total over this page
            pageTotal = api
                .column(mwh_column, { page: 'current' })
                .data()
                .reduce((a, b) => intVal(a) + intVal(b), 0);
     
            // Update footer
            api.column(mwh_column).footer().innerHTML = 
                (pageTotal / 1000).toFixed(1) + 'k<br>' + (total / 1000).toFixed(1) + 'k';
            

            // mw
            // Total over all pages
            total = api
                .column(mw_column, {filter: 'applied'})
                .data()
                .reduce((a, b) => intVal(a) + intVal(b), 0);
     
            // Total over this page
            pageTotal = api
                .column(mw_column, { page: 'current' })
                .data()
                .reduce((a, b) => intVal(a) + intVal(b), 0);
     
            // Update footer
            api.column(mw_column).footer().innerHTML = 
                (pageTotal / 1000).toFixed(1) + 'k<br>' + (total / 1000).toFixed(1) + 'k';


            // project count
            pageTotal = api.column(1, {page: 'current' }).nodes().length
            total = api.column(1, {filter: 'applied'}).nodes().length
            api.column(1).footer().innerHTML = `${pageTotal}<br>${total}`;
        } // end footerCallback

    });
}